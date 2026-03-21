import sqlite3
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import subprocess
import os

from config import config
from src.zip_exporter import ZipExporter

class JobManager:
    def __init__(self, db_path=None):
        self.db_path = db_path or config.LOG_DIR / "run_track.db"
        self.zip_exporter = ZipExporter(db_path=self.db_path)

    def create_job(self, playlist_url: str, summary_style: str = "detailed") -> str:
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        now = datetime.now()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO web_jobs (job_id, job_type, status, playlist_url, summary_style, created_at, updated_at)
                VALUES (?, 'playlist', 'queued', ?, ?, ?, ?)
                """,
                (job_id, playlist_url, summary_style, now, now)
            )
            conn.commit()
        return job_id

    def update_job(self, job_id: str, status: str, **kwargs):
        now = datetime.now()
        set_clause = "status = ?, updated_at = ?"
        params = [status, now]
        
        for k, v in kwargs.items():
            set_clause += f", {k} = ?"
            params.append(v)
            
        params.append(job_id)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"UPDATE web_jobs SET {set_clause} WHERE job_id = ?", params)
            conn.commit()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM web_jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def get_recent_jobs(self, limit: int = 10) -> list:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM web_jobs ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def run_playlist_job(self, job_id: str, playlist_url: str, api_key: Optional[str] = None, 
                         summary_style: str = "detailed", github_upload: bool = False):
        self.update_job(job_id, 'running')
        
        # Here we call the pipeline through main.py
        env = os.environ.copy()
        if api_key:
            env["OPENROUTER_API_KEY"] = api_key
            
        cmd = ["python", "src/main.py", "-list", playlist_url, "--style", summary_style]
        if github_upload:
            cmd.append("--upload")
            
        try:
            # We run the command synchronously for demonstration and capture inside the task thread
            subprocess.run(cmd, env=env, check=False)
            
            # Create ZIP bundle
            zip_path = self.zip_exporter.create_bundle(job_id)
            
            self.update_job(job_id, 'completed', zip_path=zip_path)
            
        except Exception as e:
            self.update_job(job_id, 'failed')
