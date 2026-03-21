import sqlite3
from typing import Dict, Any, Optional
from config import config

class DashboardService:
    def __init__(self, db_path=None):
        self.db_path = db_path or config.LOG_DIR / "run_track.db"

    def get_stats(self) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT status, COUNT(*) FROM runs GROUP BY status")
                statuses = {row[0]: row[1] for row in cursor.fetchall()}
                
                total = sum(statuses.values())
                completed = statuses.get("COMPLETED", 0)
                failed = statuses.get("DOWNLOAD_FAILED", 0) + statuses.get("TRANSCRIBE_FAILED", 0) + \
                         statuses.get("SUMMARIZE_FAILED", 0) + statuses.get("UPLOAD_FAILED", 0)
                reused = statuses.get("REUSED_EXISTING_REPORT", 0)
                
                return {
                    "total": total,
                    "completed": completed,
                    "failed": failed,
                    "reused": reused,
                    "by_status": statuses
                }
            except Exception as e:
                return {}

    def get_runs(self, page: int = 1, page_size: int = 10, uploader: Optional[str] = None, 
                 status: Optional[str] = None, search: Optional[str] = None) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            try:
                query = "SELECT * FROM runs WHERE 1=1"
                params = []
                
                if status:
                    query += " AND status = ?"
                    params.append(status)
                    
                if search:
                    query += " AND (url_or_path LIKE ? OR identifier LIKE ?)"
                    params.extend([f"%{search}%", f"%{search}%"])
                    
                count_query = query.replace("SELECT *", "SELECT COUNT(*)")
                cursor.execute(count_query, params)
                total = cursor.fetchone()[0]
                
                query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
                params.extend([page_size, (page - 1) * page_size])
                
                cursor.execute(query, params)
                runs = [dict(row) for row in cursor.fetchall()]
                
                # Retrieve files
                for run in runs:
                    cursor.execute("SELECT file_type, file_path, github_url FROM file_storage WHERE run_id = ?", (run["id"],))
                    files = cursor.fetchall()
                    run["files"] = [dict(f) for f in files]
                    
                return {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "items": runs
                }
            except Exception as e:
                return {"total": 0, "items": []}
