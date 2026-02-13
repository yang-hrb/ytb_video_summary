import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import config

logger = logging.getLogger(__name__)


class RunTracker:
    """Track video/MP3 processing runs in SQLite database"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.LOG_DIR / "run_track.db"
        self._init_database()

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

                cursor.execute("PRAGMA table_info(runs)")
                columns = [row[1] for row in cursor.fetchall()]
                if "stage" not in columns:
                    cursor.execute("ALTER TABLE runs ADD COLUMN stage TEXT")
                    logger.info("Added stage column to runs table")

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

    def get_resumable_runs(self, statuses: Optional[List[str]] = None) -> list:
        statuses = statuses or ["TRANSCRIPT_GENERATED", "SUMMARY_FAILED"]
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
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                query = "SELECT * FROM runs WHERE status IN ('failed', 'SUMMARY_FAILED') ORDER BY started_at DESC"
                if limit:
                    query += f" LIMIT {limit}"
                cursor.execute(query)
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


def log_failure(run_type: str, identifier: str, url_or_path: str, error_message: str):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"failures_{timestamp}.txt"
    log_path = config.LOG_DIR / log_filename

    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write("=== Failure Report ===\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Type: {run_type}\n")
            f.write(f"Identifier: {identifier}\n")
            f.write(f"URL/Path: {url_or_path}\n")
            f.write(f"Error: {error_message}\n")
            f.write(f"{'=' * 50}\n\n")

        logger.info("Failure logged to: %s", log_path)
    except Exception as e:
        logger.error("Failed to write failure log: %s", e)


_tracker = None


def get_tracker() -> RunTracker:
    global _tracker
    if _tracker is None:
        _tracker = RunTracker()
    return _tracker
