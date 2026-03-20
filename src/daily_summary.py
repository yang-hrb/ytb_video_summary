import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from config import config
from src.run_tracker import get_tracker

logger = logging.getLogger(__name__)

def generate_daily_summary(target_date: str = None, upload: bool = True):
    """
    Generate a markdown summary report of all completed runs for a given day.
    target_date should be YYYYMMDD. Defaults to today.
    """
    if not target_date:
        target_date = datetime.now().strftime("%Y%m%d")
        
    date_parsed = datetime.strptime(target_date, "%Y%m%d")
    year_month = date_parsed.strftime("%Y_%m")
    day_str = date_parsed.strftime("%Y-%m-%d")

    tracker = get_tracker()
    
    with sqlite3.connect(tracker.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("""
            SELECT r.*, f.file_path, f.github_url
            FROM runs r
            LEFT JOIN file_storage f ON r.id = f.run_id AND f.file_type = 'report' AND f.deleted_at IS NULL
            WHERE r.status IN ('COMPLETED', 'REUSED_EXISTING_REPORT')
              AND date(r.end_time) = ?
            ORDER BY r.end_time DESC
        """, (day_str,))
        
        runs = [dict(row) for row in cur.fetchall()]
        
    if not runs:
        logger.info(f"No completed runs found for {day_str}. Skipping daily summary.")
        return None
        
    total_videos = len(runs)
    total_duration = sum(r.get('duration_seconds', 0) or 0 for r in runs)
    
    content = [
        f"# Daily Summary for {day_str}",
        "",
        "## Statistics",
        f"- Total Processed: {total_videos}",
        f"- Total Audio Duration: {total_duration // 3600}h {(total_duration % 3600) // 60}m {total_duration % 60}s",
        "",
        "## Processed Content",
        "| Uploader / Name | Title | Source / Model | Report Link |",
        "| --- | --- | --- | --- |"
    ]
    
    for r in runs:
        video_id = r.get('identifier', '')
        filename = ""
        gurl = r.get('github_url')
        if r.get('file_path'):
            filename = Path(r['file_path']).stem
        
        uploader, title = "Unknown", filename
        parts = filename.split('_', 2)
        if len(parts) >= 3:
            uploader, title = parts[1], parts[2]
            
        model = r.get('model_used') or 'N/A'
        link = f"[Report]({gurl})" if gurl else (filename if filename else video_id)
        
        row_str = f"| {uploader} | {title} | {model} | {link} |"
        content.append(row_str)
        
    out_dir = config.REPORT_DIR / 'daily_summary' / year_month
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_dir / f"{day_str}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(content) + "\n")
        
    logger.info(f"Daily summary generated at {report_file}")
    
    if upload:
        try:
            from src.github_handler import upload_to_github
            remote_url = upload_to_github(
                report_file, 
                remote_folder="summary/daily_summary", 
                use_month_folder=True
            )
            logger.info(f"Daily summary uploaded: {remote_url}")
            return remote_url
        except Exception as e:
            logger.error(f"Failed to upload daily summary: {e}")
            
    return str(report_file)
