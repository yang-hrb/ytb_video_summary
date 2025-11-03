import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
from config import config

logger = logging.getLogger(__name__)


class RunTracker:
    """Track video/MP3 processing runs in SQLite database"""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize run tracker

        Args:
            db_path: Path to database file (defaults to logs/run_track.db)
        """
        self.db_path = db_path or config.LOG_DIR / "run_track.db"
        self._init_database()

    def _init_database(self):
        """Initialize database and create table if not exists"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        type TEXT NOT NULL,
                        url_or_path TEXT NOT NULL,
                        identifier TEXT NOT NULL,
                        status TEXT NOT NULL,
                        started_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL,
                        error_message TEXT
                    )
                """)
                # Create index for faster lookups
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_identifier
                    ON runs(identifier)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_status
                    ON runs(status)
                """)
                conn.commit()
                logger.debug(f"Database initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def start_run(self, run_type: str, url_or_path: str, identifier: str) -> int:
        """
        Record the start of a processing run

        Args:
            run_type: Type of run ('youtube' or 'local')
            url_or_path: URL for YouTube videos or file path for local MP3s
            identifier: Video ID for YouTube or MP3 filename for local

        Returns:
            Run ID
        """
        now = datetime.now()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO runs (type, url_or_path, identifier, status, started_at, updated_at)
                    VALUES (?, ?, ?, 'start', ?, ?)
                """, (run_type, url_or_path, identifier, now, now))
                conn.commit()
                run_id = cursor.lastrowid
                logger.info(f"Started tracking run {run_id}: {run_type} - {identifier}")
                return run_id
        except Exception as e:
            logger.error(f"Failed to start run tracking: {e}")
            raise

    def update_status(self, run_id: int, status: str, error_message: Optional[str] = None):
        """
        Update the status of a processing run

        Args:
            run_id: Run ID
            status: New status ('working', 'done', 'failed')
            error_message: Optional error message for failed runs
        """
        now = datetime.now()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if error_message:
                    cursor.execute("""
                        UPDATE runs
                        SET status = ?, updated_at = ?, error_message = ?
                        WHERE id = ?
                    """, (status, now, error_message, run_id))
                else:
                    cursor.execute("""
                        UPDATE runs
                        SET status = ?, updated_at = ?
                        WHERE id = ?
                    """, (status, now, run_id))
                conn.commit()
                logger.debug(f"Updated run {run_id} status to: {status}")
        except Exception as e:
            logger.error(f"Failed to update run status: {e}")
            raise

    def get_run_info(self, run_id: int) -> Optional[Dict]:
        """
        Get information about a specific run

        Args:
            run_id: Run ID

        Returns:
            Dictionary with run information or None if not found
        """
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
            logger.error(f"Failed to get run info: {e}")
            return None

    def get_failed_runs(self, limit: Optional[int] = None) -> list:
        """
        Get list of failed runs

        Args:
            limit: Optional limit on number of results

        Returns:
            List of failed run dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                query = "SELECT * FROM runs WHERE status = 'failed' ORDER BY started_at DESC"
                if limit:
                    query += f" LIMIT {limit}"
                cursor.execute(query)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get failed runs: {e}")
            return []

    def get_stats(self) -> Dict:
        """
        Get statistics about all runs

        Returns:
            Dictionary with run statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Total runs by status
                cursor.execute("""
                    SELECT status, COUNT(*) as count
                    FROM runs
                    GROUP BY status
                """)
                status_counts = {row[0]: row[1] for row in cursor.fetchall()}

                # Total runs by type
                cursor.execute("""
                    SELECT type, COUNT(*) as count
                    FROM runs
                    GROUP BY type
                """)
                type_counts = {row[0]: row[1] for row in cursor.fetchall()}

                return {
                    'by_status': status_counts,
                    'by_type': type_counts,
                    'total': sum(status_counts.values())
                }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {'by_status': {}, 'by_type': {}, 'total': 0}


def log_failure(run_type: str, identifier: str, url_or_path: str, error_message: str):
    """
    Log a failed run to a timestamped failure log file

    Args:
        run_type: Type of run ('youtube' or 'local')
        identifier: Video ID or MP3 filename
        url_or_path: URL or file path
        error_message: Error message
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"failures_{timestamp}.txt"
    log_path = config.LOG_DIR / log_filename

    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"=== Failure Report ===\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Type: {run_type}\n")
            f.write(f"Identifier: {identifier}\n")
            f.write(f"URL/Path: {url_or_path}\n")
            f.write(f"Error: {error_message}\n")
            f.write(f"{'=' * 50}\n\n")

        logger.info(f"Failure logged to: {log_path}")
    except Exception as e:
        logger.error(f"Failed to write failure log: {e}")


# Global tracker instance
_tracker = None


def get_tracker() -> RunTracker:
    """Get or create global RunTracker instance"""
    global _tracker
    if _tracker is None:
        _tracker = RunTracker()
    return _tracker
