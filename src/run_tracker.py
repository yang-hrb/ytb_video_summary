import csv
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from config import config
from src.database import DatabaseManager
from src.exceptions import DatabaseError

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Issue 02: dedup store — single source of truth for "done or not".
# New DB logs/ytb_summary_track.db, single table `videos`.
# Reads/writes go through the existing DatabaseManager (no new wrapper).
# Status vocabulary is this one FAILED_STATUSES tuple (no Enum).
# ------------------------------------------------------------------

FAILED_STATUSES = (
    'DOWNLOAD_FAILED', 'TRANSCRIBE_FAILED',
    'SUMMARIZE_FAILED', 'SUMMARY_FAILED',
    'UPLOAD_FAILED', 'failed',
)

NEW_TRACK_DB_NAME = "ytb_summary_track.db"
OLD_TRACK_DB_NAME = "run_track.db"
BACKUP_TRACK_DB_NAME = "run_track_backup.db"
TWO_TIME_FAIL_NAME = "two_time_fail.txt"

# ponytail: cap hashing at head MB + file size so multi-GB MP3s stay cheap
LOCAL_HASH_HEAD_MB = 8

_VIDEOS_DDL = """
CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    channel_url TEXT,
    publish_date TEXT,
    first_seen TEXT NOT NULL,
    md_path TEXT,
    github_url TEXT,
    status TEXT NOT NULL,
    fail_count INTEGER DEFAULT 0,
    last_error TEXT,
    updated_at TEXT NOT NULL,
    uploader TEXT,
    title TEXT,
    duration_seconds INTEGER DEFAULT 0
)
"""

# Columns added after the issue-02 DDL (spec §6.1: digest reads these directly).
_VIDEOS_EXTRA_COLUMNS = [
    ("uploader", "TEXT"),
    ("title", "TEXT"),
    ("duration_seconds", "INTEGER DEFAULT 0"),
]


def two_time_fail_path() -> Path:
    return config.LOG_DIR / TWO_TIME_FAIL_NAME


def dedup_db_path() -> Path:
    return config.LOG_DIR / NEW_TRACK_DB_NAME


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_videos_table(db: DatabaseManager):
    db.execute_update(_VIDEOS_DDL)
    cols = {row['name'] for row in db.execute("PRAGMA table_info(videos)")}
    for col_name, col_def in _VIDEOS_EXTRA_COLUMNS:
        if col_name not in cols:
            db.execute_update(f"ALTER TABLE videos ADD COLUMN {col_name} {col_def}")


def local_content_id(mp3_path: Path, head_mb: int = LOCAL_HASH_HEAD_MB) -> str:
    """Stable content-based id: local_<sha256[:16]>. Rename-proof, content-sensitive."""
    h = hashlib.sha256()
    size = 0
    limit = head_mb * 1024 * 1024
    with open(mp3_path, 'rb') as f:
        while size < limit:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
            size += len(chunk)
    h.update(str(Path(mp3_path).stat().st_size).encode())
    return f"local_{h.hexdigest()[:16]}"


def get_dedup_db(db_path: Optional[Path] = None) -> DatabaseManager:
    """Open the new dedup DB (creating videos table + running migration as needed)."""
    path = Path(db_path) if db_path else dedup_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = DatabaseManager(path)
    init_videos_table(db)
    if path == dedup_db_path():
        migrate_legacy_db()
    return db


def find_completed_video(db: DatabaseManager, video_id: str) -> Optional[Dict]:
    if not video_id:
        return None
    return db.execute_one(
        "SELECT * FROM videos WHERE video_id = ? AND status = 'COMPLETED'",
        (video_id,),
    )


def mark_video_completed(db: DatabaseManager, video_id: str, url: str,
                          md_path: Optional[str] = None,
                          github_url: Optional[str] = None,
                          channel_url: Optional[str] = None,
                          publish_date: Optional[str] = None,
                          uploader: Optional[str] = None,
                          title: Optional[str] = None,
                          duration_seconds: Optional[int] = None):
    now = _now_str()
    db.execute_update(
        "INSERT OR IGNORE INTO videos (video_id, url, first_seen, status, updated_at)"
        " VALUES (?, ?, ?, 'COMPLETED', ?)",
        (video_id, url, now, now),
    )
    db.execute_update(
        "UPDATE videos SET url = ?, md_path = ?, github_url = ?, channel_url = ?,"
        " publish_date = ?, uploader = ?, title = ?, duration_seconds = ?,"
        " status = 'COMPLETED', last_error = NULL, updated_at = ?"
        " WHERE video_id = ?",
        (url, md_path, github_url, channel_url, publish_date, uploader, title,
         duration_seconds, now, video_id),
    )


def mark_video_failed(db: DatabaseManager, video_id: str, url: str, error: str) -> int:
    """Record a FAILED run, bumping fail_count. Returns the new fail_count.

    On the 2nd failure (fail_count == 2) appends one stdlib-csv line to
    logs/two_time_fail.txt: video_id,url,第一次失败时间,第二次失败时间,错误.
    """
    now = _now_str()
    prev = db.execute_one("SELECT fail_count, updated_at FROM videos WHERE video_id = ?",
                          (video_id,))
    prev_fail_time = prev.get('updated_at') if prev else None
    db.execute_update(
        "INSERT OR IGNORE INTO videos (video_id, url, first_seen, status, fail_count, updated_at)"
        " VALUES (?, ?, ?, 'FAILED', 0, ?)",
        (video_id, url, now, now),
    )
    db.execute_update(
        "UPDATE videos SET url = ?, status = 'FAILED',"
        " fail_count = COALESCE(fail_count, 0) + 1, last_error = ?, updated_at = ?"
        " WHERE video_id = ?",
        (url, error, now, video_id),
    )
    row = db.execute_one("SELECT fail_count FROM videos WHERE video_id = ?", (video_id,))
    fail_count = (row.get('fail_count') if row else None) or 0
    if fail_count == 2:
        _append_two_time_fail(video_id, url, prev_fail_time or now, now, error)
    return fail_count


def _append_two_time_fail(video_id: str, url: str, first_fail: str, second_fail: str,
                          error: str):
    """Append one CSV line for a twice-failed video (spec §6.3)."""
    try:
        path = two_time_fail_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'a', encoding='utf-8', newline='') as f:
            csv.writer(f).writerow([video_id, url, first_fail, second_fail, error])
    except OSError as e:
        logger.warning("Failed to write %s: %s", TWO_TIME_FAIL_NAME, e)


def mark_video_pending_killed(db: DatabaseManager, video_id: str, url: str):
    """Mark a timeout-killed video as not-run: fail_count untouched (spec §5).

    Never clobbers a COMPLETED row (late finish wins over the killer).
    """
    now = _now_str()
    db.execute_update(
        "INSERT OR IGNORE INTO videos (video_id, url, first_seen, status, fail_count, updated_at)"
        " VALUES (?, ?, ?, 'PENDING_KILLED', 0, ?)",
        (video_id, url, now, now),
    )
    db.execute_update(
        "UPDATE videos SET url = ?, status = 'PENDING_KILLED', updated_at = ?"
        " WHERE video_id = ? AND status != 'COMPLETED'",
        (url, now, video_id),
    )


def migrate_legacy_db(new_db_path: Optional[Path] = None,
                      old_db_path: Optional[Path] = None,
                      backup_db_path: Optional[Path] = None) -> dict:
    """Rename old DB to backup and import COMPLETED rows once. Idempotent.

    - old exists, backup missing → rename (incl. -wal/-shm sidecars), import from backup.
    - both exist → import from old too, then remove redundant old file.
    - only backup exists → import only when videos table is empty (backup is frozen).
    - neither exists → no-op (compatible with fresh checkouts).
    """
    new_path = Path(new_db_path) if new_db_path else dedup_db_path()
    old_path = Path(old_db_path) if old_db_path else config.LOG_DIR / OLD_TRACK_DB_NAME
    bak_path = Path(backup_db_path) if backup_db_path else config.LOG_DIR / BACKUP_TRACK_DB_NAME
    stats = {'renamed': False, 'imported': 0}

    new_path.parent.mkdir(parents=True, exist_ok=True)
    new_db = DatabaseManager(new_path)
    init_videos_table(new_db)

    sources: List[Path] = []
    if old_path.exists():
        if not bak_path.exists():
            old_path.rename(bak_path)
            for suffix in ("-wal", "-shm"):
                sidecar = Path(str(old_path) + suffix)
                if sidecar.exists():
                    sidecar.rename(Path(str(bak_path) + suffix))
            stats['renamed'] = True
        sources.append(bak_path if bak_path.exists() else old_path)
        if bak_path.exists() and old_path.exists() and bak_path != old_path:
            # Both present (e.g. legacy write re-created old): import then drop the redundant copy.
            if old_path not in sources:
                sources.append(old_path)
    elif bak_path.exists():
        count = new_db.execute_one("SELECT COUNT(*) AS n FROM videos")
        if not count or count.get('n', 0) == 0:
            sources.append(bak_path)

    for src in sources:
        stats['imported'] += _import_completed_from(src, new_db)
        if src == old_path and bak_path.exists():
            try:
                old_path.unlink()
            except OSError:
                pass
    return stats


def _import_completed_from(src: Path, new_db: DatabaseManager) -> int:
    try:
        src_db = DatabaseManager(src)
        cols = {row['name'] for row in src_db.execute("PRAGMA table_info(runs)")}
    except DatabaseError as e:
        logger.warning("Skipping legacy import from %s: %s", src, e)
        return 0
    if 'identifier' not in cols:
        return 0
    select_cols = ['identifier', 'url_or_path', 'started_at', 'updated_at']
    for optional in ('report_path', 'github_url'):
        if optional in cols:
            select_cols.append(optional)
    try:
        rows = src_db.execute(
            f"SELECT {', '.join(select_cols)} FROM runs WHERE status = 'COMPLETED'"
        )
    except DatabaseError as e:
        logger.warning("Skipping legacy import from %s: %s", src, e)
        return 0
    imported = 0
    for r in rows:
        vid = r.get('identifier')
        if not vid:
            continue
        first_seen = r.get('started_at') or r.get('updated_at') or _now_str()
        try:
            new_db.execute_update(
                "INSERT OR IGNORE INTO videos"
                " (video_id, url, first_seen, md_path, github_url, status, updated_at)"
                " VALUES (?, ?, ?, ?, ?, 'COMPLETED', ?)",
                (vid, r.get('url_or_path') or '', str(first_seen),
                 r.get('report_path'), r.get('github_url'),
                 str(r.get('updated_at') or first_seen)),
            )
            imported += 1
        except DatabaseError as e:
            logger.warning("Legacy row import failed for %s: %s", vid, e)
    if imported:
        logger.info("Imported %d COMPLETED row(s) from %s", imported, src)
    return imported


class RunTracker:
    """Track video/MP3 processing runs in SQLite database"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.LOG_DIR / "run_track.db"
        self.db = DatabaseManager(self.db_path)
        self._init_database()

    # Phase-2 columns added to existing runs table
    _PHASE2_COLUMNS = [
        ("transcript_path", "TEXT"),
        ("summary_path", "TEXT"),
        ("report_path", "TEXT"),
        ("github_url", "TEXT"),
        ("model_used", "TEXT"),
        ("audio_path", "TEXT"),
        ("summary_style", "TEXT"),
        ("retry_count", "INTEGER DEFAULT 0"),
    ]

    # Phase-3 columns added to existing runs table
    _PHASE3_COLUMNS = [
        ("prompt_type", "TEXT"),
        ("prompt_source", "TEXT"),
        ("prompt_index", "INTEGER"),
        ("prompt_file", "TEXT"),
    ]

    def _init_database(self):
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        type TEXT NOT NULL,
                        url_or_path TEXT NOT NULL,
                        identifier TEXT NOT NULL,
                        status TEXT NOT NULL,
                        stage TEXT,
                        started_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL,
                        error_message TEXT
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_identifier
                    ON runs(identifier)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_status
                    ON runs(status)
                    """
                )

                # Phase 3: file_storage table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS file_storage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_id INTEGER NOT NULL,
                        file_type TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        file_size INTEGER,
                        github_url TEXT,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL,
                        deleted_at TIMESTAMP,
                        FOREIGN KEY (run_id) REFERENCES runs(id)
                    )
                    """
                )
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fs_run_id ON file_storage(run_id)")

                # Phase 3: watch_channels table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS watch_channels (
                        channel_id TEXT PRIMARY KEY,
                        name TEXT,
                        platform TEXT DEFAULT 'youtube',
                        added_at TIMESTAMP NOT NULL,
                        is_active BOOLEAN DEFAULT 1
                    )
                    """
                )

                # Phase 3: watch_channel_state table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS watch_channel_state (
                        channel_id TEXT PRIMARY KEY,
                        last_scan_time TIMESTAMP NOT NULL,
                        last_seen_upload_date TEXT,
                        last_seen_video_id TEXT,
                        videos_processed_total INTEGER DEFAULT 0,
                        FOREIGN KEY (channel_id) REFERENCES watch_channels(channel_id)
                    )
                    """
                )

                # Phase 3: watch_scan_runs table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS watch_scan_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        scan_start TIMESTAMP NOT NULL,
                        scan_end TIMESTAMP,
                        channels_scanned INTEGER DEFAULT 0,
                        new_videos_found INTEGER DEFAULT 0,
                        videos_processed INTEGER DEFAULT 0,
                        errors_count INTEGER DEFAULT 0,
                        status TEXT NOT NULL
                    )
                    """
                )

                # Phase 4: web_jobs table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS web_jobs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT NOT NULL UNIQUE,
                        job_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        playlist_url TEXT,
                        summary_style TEXT,
                        total_count INTEGER DEFAULT 0,
                        completed_count INTEGER DEFAULT 0,
                        failed_count INTEGER DEFAULT 0,
                        reused_count INTEGER DEFAULT 0,
                        zip_path TEXT,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                    """
                )

                # Phase 4: web_job_runs table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS web_job_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT NOT NULL,
                        run_id INTEGER NOT NULL,
                        created_at TIMESTAMP NOT NULL
                    )
                    """
                )

                cursor.execute("PRAGMA table_info(runs)")
                columns = [row[1] for row in cursor.fetchall()]

                # Backward-compatible migrations
                if "stage" not in columns:
                    cursor.execute("ALTER TABLE runs ADD COLUMN stage TEXT")
                    logger.info("Added stage column to runs table")

                for col_name, col_def in self._PHASE2_COLUMNS + self._PHASE3_COLUMNS:
                    if col_name not in columns:
                        cursor.execute(
                            f"ALTER TABLE runs ADD COLUMN {col_name} {col_def}"
                        )
                        logger.info("Added column %s to runs table", col_name)

                conn.commit()
                logger.debug("Database initialized: %s", self.db_path)
        except Exception as e:
            logger.error("Failed to initialize database: %s", e)
            raise

    def start_run(self, run_type: str, url_or_path: str, identifier: str) -> int:
        now = datetime.now()
        try:
            run_id = self.db.execute_insert(
                """
                INSERT INTO runs (type, url_or_path, identifier, status, stage, started_at, updated_at)
                VALUES (?, ?, ?, 'PENDING', 'INIT', ?, ?)
                """,
                (run_type, url_or_path, identifier, now, now),
            )
            logger.info("Started tracking run %s: %s - %s", run_id, run_type, identifier)
            return run_id
        except DatabaseError as e:
            logger.error("Failed to start run tracking: %s", e)
            raise

    def update_status(self, run_id: int, status: str, error_message: Optional[str] = None, stage: Optional[str] = None):
        now = datetime.now()
        try:
            set_clause = "status = ?, updated_at = ?"
            params: List = [status, now]

            if stage is not None:
                set_clause += ", stage = ?"
                params.append(stage)

            if error_message is not None:
                set_clause += ", error_message = ?"
                params.append(error_message)

            params.append(run_id)
            self.db.execute_update(f"UPDATE runs SET {set_clause} WHERE id = ?", tuple(params))
            logger.debug("Updated run %s status to: %s", run_id, status)
        except DatabaseError as e:
            logger.error("Failed to update run status: %s", e)
            raise

    def update_artifacts(self, run_id: int, **kwargs):
        """Batch-update artifact paths and metadata for a run.

        Accepted keyword arguments (all optional):
            transcript_path, summary_path, report_path, github_url,
            model_used, audio_path, summary_style
        """
        allowed = {
            "transcript_path", "summary_path", "report_path",
            "github_url", "model_used", "audio_path", "summary_style",
            "prompt_type", "prompt_source", "prompt_index", "prompt_file",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not updates:
            return
        now = datetime.now()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        set_clause += ", updated_at = ?"
        params = list(updates.values()) + [now, run_id]
        try:
            self.db.execute_update(f"UPDATE runs SET {set_clause} WHERE id = ?", tuple(params))
            logger.debug("Updated artifacts for run %s: %s", run_id, list(updates))
        except DatabaseError as e:
            logger.error("Failed to update artifacts for run %s: %s", run_id, e)
            raise

    def increment_retry(self, run_id: int):
        now = datetime.now()
        try:
            self.db.execute_update(
                "UPDATE runs SET retry_count = COALESCE(retry_count, 0) + 1, updated_at = ? WHERE id = ?",
                (now, run_id),
            )
            logger.debug("Incremented retry_count for run %s", run_id)
        except DatabaseError as e:
            logger.error("Failed to increment retry count for run %s: %s", run_id, e)
            raise

    def get_run_info(self, run_id: int) -> Optional[Dict]:
        try:
            return self.db.execute_one("SELECT * FROM runs WHERE id = ?", (run_id,))
        except DatabaseError as e:
            logger.error("Failed to get run info: %s", e)
            return None

    # All statuses from which a run can be recovered without restarting from scratch.
    RESUMABLE_STATUS_MAP: Dict[str, str] = {
        'DOWNLOAD_FAILED':   'download',
        'TRANSCRIBE_FAILED': 'transcribe',
        'TRANSCRIPT_READY':  'summarize',
        'TRANSCRIPT_GENERATED': 'summarize',  # legacy alias
        'SUMMARIZE_FAILED':  'summarize',
        'SUMMARY_FAILED':    'summarize',      # legacy alias
        'SUMMARY_READY':     'upload',
        'UPLOAD_FAILED':     'upload',
    }

    def get_resumable_runs(self, statuses: Optional[List[str]] = None) -> list:
        statuses = statuses or list(self.RESUMABLE_STATUS_MAP.keys())
        placeholders = ",".join("?" for _ in statuses)
        try:
            return self.db.execute(
                f"SELECT * FROM runs WHERE status IN ({placeholders}) ORDER BY updated_at ASC",
                tuple(statuses),
            )
        except DatabaseError as e:
            logger.error("Failed to get resumable runs: %s", e)
            return []

    def get_failed_runs(self, limit: Optional[int] = None) -> list:
        placeholders = ",".join("?" for _ in FAILED_STATUSES)
        try:
            query = f"SELECT * FROM runs WHERE status IN ({placeholders}) ORDER BY started_at DESC"
            if limit:
                query += f" LIMIT {limit}"
            return self.db.execute(query, FAILED_STATUSES)
        except DatabaseError as e:
            logger.error("Failed to get failed runs: %s", e)
            return []

    def get_stats(self) -> Dict:
        try:
            status_rows = self.db.execute("SELECT status, COUNT(*) as count FROM runs GROUP BY status")
            status_counts = {row['status']: row['count'] for row in status_rows}

            type_rows = self.db.execute("SELECT type, COUNT(*) as count FROM runs GROUP BY type")
            type_counts = {row['type']: row['count'] for row in type_rows}

            return {
                "by_status": status_counts,
                "by_type": type_counts,
                "total": sum(status_counts.values()),
            }
        except DatabaseError as e:
            logger.error("Failed to get stats: %s", e)
            return {"by_status": {}, "by_type": {}, "total": 0}

    # ------------------------------------------------------------------
    # Phase 3: file_storage methods
    # ------------------------------------------------------------------
    def register_file(self, run_id: int, file_type: str, file_path: str, file_size: Optional[int] = None, github_url: Optional[str] = None) -> int:
        now = datetime.now()
        return self.db.execute_insert(
            """
            INSERT INTO file_storage (run_id, file_type, file_path, file_size, github_url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, file_type, file_path, file_size, github_url, now, now)
        )

    def get_files_for_run(self, run_id: int, file_type: Optional[str] = None) -> List[dict]:
        query = "SELECT * FROM file_storage WHERE run_id = ? AND deleted_at IS NULL"
        params: list = [run_id]
        if file_type:
            query += " AND file_type = ?"
            params.append(file_type)
        return self.db.execute(query, tuple(params))

    def mark_file_deleted(self, file_storage_id: int):
        now = datetime.now()
        self.db.execute_update(
            "UPDATE file_storage SET deleted_at = ?, updated_at = ? WHERE id = ?",
            (now, now, file_storage_id)
        )

    def update_file_github_url(self, file_storage_id: int, github_url: str):
        now = datetime.now()
        self.db.execute_update(
            "UPDATE file_storage SET github_url = ?, updated_at = ? WHERE id = ?",
            (github_url, now, file_storage_id)
        )

    def find_latest_completed_report(self, identifier: str) -> Optional[dict]:
        query = """
        SELECT fs.*, r.id as r_id
        FROM runs r
        JOIN file_storage fs ON r.id = fs.run_id
        WHERE r.identifier = ? AND r.status = 'COMPLETED'
          AND fs.file_type = 'report' AND fs.deleted_at IS NULL
        ORDER BY r.updated_at DESC LIMIT 1
        """
        return self.db.execute_one(query, (identifier,))


# Module-level variable: same process reuses the same failure log file for the entire session.
# This prevents the logs/ directory from accumulating one file per failure (was 80+ files).
_session_failure_log = None


def log_failure(run_type: str, identifier: str, url_or_path: str,
                error_message: str, stage: str = None):
    """Log a failure to the session failure file (one file per process session).

    Args:
        run_type: Type of run ('youtube', 'local', 'podcast')
        identifier: Video ID or file name
        url_or_path: Original URL or file path
        error_message: Error description
        stage: Pipeline stage where failure occurred ('download', 'transcribe', 'summarize', 'upload')
    """
    global _session_failure_log
    if _session_failure_log is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _session_failure_log = config.LOG_DIR / f"failures_{timestamp}.txt"

    try:
        with open(_session_failure_log, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] "
                    f"stage={stage or 'unknown'} | type={run_type} | id={identifier}\n")
            f.write(f"  URL/Path: {url_or_path}\n")
            f.write(f"  Error: {error_message}\n\n")

        logger.info("Failure logged to: %s", _session_failure_log)
    except Exception as e:
        logger.error("Failed to write failure log: %s", e)


_tracker = None


def get_tracker() -> RunTracker:
    global _tracker
    if _tracker is None:
        _tracker = RunTracker()
    return _tracker


def cleanup_old_logs(log_dir: Path = None, keep_days: int = 30):
    """Remove failure log files older than keep_days days.

    Args:
        log_dir: Directory containing log files (defaults to config.LOG_DIR)
        keep_days: Number of days to retain log files (default: 30)
    """
    log_dir = log_dir or config.LOG_DIR
    if not log_dir.exists():
        return

    cutoff = datetime.now() - timedelta(days=keep_days)
    removed = 0
    for f in log_dir.glob('failures_*.txt'):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                f.unlink()
                removed += 1
        except Exception as e:
            logger.warning("Could not remove old log file %s: %s", f.name, e)

    if removed:
        logger.info("Cleaned up %d old failure log file(s) from %s", removed, log_dir)
