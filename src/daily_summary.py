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
    timestamp_str = datetime.now().strftime("%H_%M")

    tracker = get_tracker()
    
    with sqlite3.connect(tracker.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("""
            SELECT r.*, f.file_path, f.github_url
            FROM runs r
            LEFT JOIN file_storage f ON r.id = f.run_id AND f.file_type = 'report' AND f.deleted_at IS NULL
            WHERE r.status IN ('COMPLETED', 'REUSED_EXISTING_REPORT')
              AND date(r.updated_at) = ?
            ORDER BY r.updated_at DESC
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
        
        uploader = "Unknown"
        title = ""
        model = r.get('model_used')

        if r.get('file_path') and Path(r['file_path']).exists():
            fpath = Path(r['file_path'])
            filename = fpath.stem
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines and lines[0].startswith('# '):
                        title = lines[0][2:].strip()
                    
                    if not model:
                        for bline in reversed(lines[-20:]):
                            if "**AI Model**:" in bline:
                                model = bline.split('**AI Model**:')[-1].strip().strip('`').strip()
                                break
            except Exception:
                pass
                
        if not title and filename:
            title = filename
        
        if filename:
            from src.utils import sanitize_filename
            clean_t = sanitize_filename(title, max_length=20)
            f_rest = filename
            parts = filename.split('_', 1)
            if len(parts) == 2 and len(parts[0]) == 8 and parts[0].isdigit():
                f_rest = parts[1]
                
            if f_rest.endswith(clean_t) and f_rest != clean_t:
                uploader_part = f_rest[:-len(clean_t)]
                uploader = uploader_part.rstrip('_').replace('_', ' ')
            else:
                pieces = f_rest.split('_', 1)
                if len(pieces) > 1:
                    uploader = pieces[0]
                else:
                    uploader = "Unknown"

        if not model:
            model = 'N/A'
            
        link = f"[Report]({gurl})" if gurl else (filename if filename else video_id)
        
        uploader = uploader.replace('|', '').replace('  ', ' ').strip()
        title = title.replace('|', '').replace('  ', ' ').strip()
        model = model.replace('|', ' ').replace('  ', ' ').strip()
        
        row_str = f"| {uploader} | {title} | {model} | {link} |"
        content.append(row_str)
        
    out_dir = config.REPORT_DIR / 'daily_digest' / year_month
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_dir / f"{day_str}-{timestamp_str}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(content) + "\n")
        
    logger.info(f"Daily summary generated at {report_file}")
    
    if upload:
        try:
            from src.github_handler import GitHubHandler
            from config import config as _cfg
            if _cfg.GITHUB_TOKEN and _cfg.GITHUB_REPO:
                handler = GitHubHandler()
                remote_path = f"daily_digest/{year_month}/{report_file.name}"
                remote_url = handler.upload_file(
                    report_file,
                    remote_path,
                    commit_message=f"Add daily digest: {report_file.name}",
                )
                logger.info(f"Daily summary uploaded: {remote_url}")
                return remote_url
        except Exception as e:
            logger.error(f"Failed to upload daily summary: {e}")

    return str(report_file)

