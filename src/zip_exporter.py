import os
import zipfile
import csv
import json
import sqlite3
import logging
from datetime import datetime
from config import config

logger = logging.getLogger(__name__)


class ZipExporter:
    def __init__(self, db_path=None):
        self.db_path = db_path or config.LOG_DIR / "run_track.db"
        self.output_dir = config.BASE_DIR / "output" / "zips"
        os.makedirs(self.output_dir, exist_ok=True)

    def create_bundle(self, job_id: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        zip_filename = f"summary_bundle_{job_id}_{timestamp}.zip"
        zip_path = os.path.join(self.output_dir, zip_filename)
        
        # Gather run_ids: For simplicity in this demo, if no linked web_job_runs exist
        # we pull recent runs that completed.
        run_ids = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT run_id FROM web_job_runs WHERE job_id = ?", (job_id,))
            run_ids = [row[0] for row in cursor.fetchall()]
        
        if not run_ids:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM runs WHERE status = 'COMPLETED' ORDER BY updated_at DESC LIMIT 10")
                run_ids = [row[0] for row in cursor.fetchall()]

        runs_data = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            for rid in run_ids:
                cursor.execute("SELECT * FROM runs WHERE id = ?", (rid,))
                rd = cursor.fetchone()
                if rd:
                    runs_data.append(dict(rd))

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Metadata CSV
            metadata_csv = os.path.join(config.TEMP_DIR, "runs.csv")
            if runs_data:
                with open(metadata_csv, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=runs_data[0].keys())
                    writer.writeheader()
                    writer.writerows(runs_data)
                zipf.write(metadata_csv, arcname="metadata/runs.csv")

            # JSON manifest
            manifest = {
                "job_id": job_id,
                "timestamp": timestamp,
                "count": len(runs_data)
            }
            manifest_path = os.path.join(config.TEMP_DIR, "job_manifest.json")
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            zipf.write(manifest_path, arcname="metadata/job_manifest.json")
            
            # Pack reports and transcripts
            for run in runs_data:
                # fetch files from file_storage Table 
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    try:
                        cursor.execute("SELECT * FROM file_storage WHERE run_id = ?", (run["id"],))
                        files = cursor.fetchall()
                        for f in files:
                            fd = dict(f)
                            if fd.get("file_path") and os.path.exists(fd["file_path"]):
                                if fd["file_type"] == "report":
                                    zipf.write(fd["file_path"], arcname=f"reports/{os.path.basename(fd['file_path'])}")
                                elif fd["file_type"] == "transcript":
                                    zipf.write(fd["file_path"], arcname=f"transcripts/{os.path.basename(fd['file_path'])}")
                    except sqlite3.OperationalError as e:
                        logger.debug(f"file_storage table not available for run {run['id']}: {e}")
                    except (KeyError, OSError) as e:
                        logger.warning(f"Error processing files for run {run['id']}: {e}")

        return zip_path
