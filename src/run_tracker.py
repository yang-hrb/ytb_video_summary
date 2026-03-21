import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from config import config

logger = logging.getLogger(__name__)


class RunTracker:
    """Track video/MP3 processing runs in SQLite database"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.LOG_DIR / "run_track.db"
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
            with sqlite3.connect(self.db_path) as conn:
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
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO runs (type, url_or_path, identifier, status, stage, started_at, updated_at)
                    VALUES (?, ?, ?, 'PENDING', 'INIT', ?, ?)
                    """,
                    (run_type, url_or_path, identifier, now, now),
                )
                conn.commit()
                run_id = cursor.lastrowid
                logger.info("Started tracking run %s: %s - %s", run_id, run_type, identifier)
                return run_id
        except Exception as e:
            logger.error("Failed to start run tracking: %s", e)
            raise

    def update_status(self, run_id: int, status: str, error_message: Optional[str] = None, stage: Optional[str] = None):
        now = datetime.now()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                set_clause = "status = ?, updated_at = ?"
                params: List = [status, now]

                if stage is not None:
                    set_clause += ", stage = ?"
                    params.append(stage)

                if error_message is not None:
                    set_clause += ", error_message = ?"
                    params.append(error_message)

                params.append(run_id)
                cursor.execute(f"UPDATE runs SET {set_clause} WHERE id = ?", tuple(params))
                conn.commit()
                logger.debug("Updated run %s status to: %s", run_id, status)
        except Exception as e:
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
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    f"UPDATE runs SET {set_clause} WHERE id = ?", params
                )
                conn.commit()
                logger.debug("Updated artifacts for run %s: %s", run_id, list(updates))
        except Exception as e:
            logger.error("Failed to update artifacts for run %s: %s", run_id, e)
            raise

    def increment_retry(self, run_id: int):
        """Increment the retry_count for a run by 1."""
        now = datetime.now()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE runs SET retry_count = COALESCE(retry_count, 0) + 1, "
                    "updated_at = ? WHERE id = ?",
                    (now, run_id),
                )
                conn.commit()
                logger.debug("Incremented retry_count for run %s", run_id)
        except Exception as e:
            logger.error("Failed to increment retry count for run %s: %s", run_id, e)
            raise

    def get_run_info(self, run_id: int) -> Optional[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
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
        """Return runs that can be resumed from a mid-pipeline stage.

        Args:
            statuses: Explicit list of statuses to query.  Defaults to all keys
                      in RESUMABLE_STATUS_MAP.
        """
        statuses = statuses or list(self.RESUMABLE_STATUS_MAP.keys())
        placeholders = ",".join("?" for _ in statuses)

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    f"""
                    SELECT * FROM runs
                    WHERE status IN ({placeholders})
                    ORDER BY updated_at ASC
                    """,
                    tuple(statuses),
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error("Failed to get resumable runs: %s", e)
            return []

    def get_failed_runs(self, limit: Optional[int] = None) -> list:
        """Return runs in any failed status."""
        failed_statuses = (
            'DOWNLOAD_FAILED', 'TRANSCRIBE_FAILED',
            'SUMMARIZE_FAILED', 'SUMMARY_FAILED',  # legacy
            'UPLOAD_FAILED', 'failed',
        )
        placeholders = ",".join("?" for _ in failed_statuses)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                query = (
                    f"SELECT * FROM runs WHERE status IN ({placeholders}) "
                    "ORDER BY started_at DESC"
                )
                if limit:
                    query += f" LIMIT {limit}"
                cursor.execute(query, failed_statuses)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error("Failed to get failed runs: %s", e)
            return []

    def get_stats(self) -> Dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT status, COUNT(*) as count
                    FROM runs
                    GROUP BY status
                    """
                )
                status_counts = {row[0]: row[1] for row in cursor.fetchall()}

                cursor.execute(
                    """
                    SELECT type, COUNT(*) as count
                    FROM runs
                    GROUP BY type
                    """
                )
                type_counts = {row[0]: row[1] for row in cursor.fetchall()}

                return {
                    "by_status": status_counts,
                    "by_type": type_counts,
                    "total": sum(status_counts.values()),
                }
        except Exception as e:
            logger.error("Failed to get stats: %s", e)
            return {"by_status": {}, "by_type": {}, "total": 0}

    # ------------------------------------------------------------------
    # Phase 3: file_storage methods
    # ------------------------------------------------------------------
    def register_file(self, run_id: int, file_type: str, file_path: str, file_size: Optional[int] = None, github_url: Optional[str] = None) -> int:
        now = datetime.now()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO file_storage (run_id, file_type, file_path, file_size, github_url, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, file_type, file_path, file_size, github_url, now, now)
            )
            conn.commit()
            return cursor.lastrowid
            
    def get_files_for_run(self, run_id: int, file_type: Optional[str] = None) -> List[dict]:
        query = "SELECT * FROM file_storage WHERE run_id = ? AND deleted_at IS NULL"
        params = [run_id]
        if file_type:
            query += " AND file_type = ?"
            params.append(file_type)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
            
    def mark_file_deleted(self, file_storage_id: int):
        now = datetime.now()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE file_storage SET deleted_at = ?, updated_at = ? WHERE id = ?", (now, now, file_storage_id))
            conn.commit()
            
    def update_file_github_url(self, file_storage_id: int, github_url: str):
        now = datetime.now()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE file_storage SET github_url = ?, updated_at = ? WHERE id = ?", (github_url, now, file_storage_id))
            conn.commit()
            
    def find_latest_completed_report(self, identifier: str) -> Optional[dict]:
        # find the latest completed run with this identifier that has a report
        query = """
        SELECT fs.*, r.id as r_id 
        FROM runs r
        JOIN file_storage fs ON r.id = fs.run_id
        WHERE r.identifier = ? AND r.status = 'COMPLETED' 
          AND fs.file_type = 'report' AND fs.deleted_at IS NULL
        ORDER BY r.updated_at DESC LIMIT 1
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, (identifier,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None


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
