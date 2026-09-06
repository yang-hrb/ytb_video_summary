import logging
from datetime import datetime
from typing import Dict, List, Optional

from config import config
from src.run_tracker import get_dedup_db

logger = logging.getLogger(__name__)


def _clean(text) -> str:
    return str(text or '').replace('|', '').replace('  ', ' ').strip()


def _row_line(r: Dict) -> str:
    uploader = _clean(r.get('uploader')) or 'Unknown'
    title = _clean(r.get('title')) or _clean(r.get('md_path')) or _clean(r.get('video_id'))
    link = r.get('github_url') or r.get('md_path') or r.get('video_id') or ''
    if r.get('github_url'):
        link = f"[Report]({r['github_url']})"
    return f"| {uploader} | {title} | {link} |"


def _fail_line(r: Dict) -> str:
    vid = _clean(r.get('video_id'))
    err = _clean(r.get('last_error'))
    return f"- 🔴 `{vid}` (fail_count={r.get('fail_count', 0)}): {err}"


def generate_daily_summary(target_date: str = None, upload: bool = True,
                           run_results: Optional[Dict[str, List[Dict]]] = None,
                           db=None):
    """
    Generate the Daily Digest for the scan start date (target_date YYYYMMDD).

    Cross-day rule (spec §6.1): the date is the 04:00 job's start day, passed in
    by the caller — a run spilling past midnight still lands in this one file
    (output/summary/daily_digest/YYYY_MM/YYYY-MM-DD.md, overwritten in place).

    Four sections: 🔴 red zone (two-time fails) / new reports / reused refs /
    unprocessed PENDING_KILLED. All fields come from the new videos-table
    columns (uploader/title/duration_seconds) — no filename guessing.
    """
    if not target_date:
        target_date = datetime.now().strftime("%Y%m%d")

    date_parsed = datetime.strptime(target_date, "%Y%m%d")
    year_month = date_parsed.strftime("%Y_%m")
    day_str = date_parsed.strftime("%Y-%m-%d")

    db = db or get_dedup_db()
    run_results = run_results or {}

    if 'new' in run_results:
        new_rows = run_results['new']
    else:
        new_rows = db.execute(
            "SELECT * FROM videos WHERE status = 'COMPLETED'"
            " AND date(updated_at) = ? ORDER BY updated_at DESC",
            (day_str,),
        )
    reused_rows = run_results.get('reused', [])
    red_rows = db.execute(
        "SELECT * FROM videos WHERE status = 'FAILED'"
        " AND COALESCE(fail_count, 0) >= 2 ORDER BY updated_at DESC"
    )
    if 'pending' in run_results:
        pending_rows = run_results['pending']
    else:
        pending_rows = db.execute(
            "SELECT * FROM videos WHERE status = 'PENDING_KILLED'"
            " ORDER BY updated_at DESC"
        )

    if not new_rows and not reused_rows and not red_rows and not pending_rows:
        logger.info(f"No completed/reused/failed/pending rows for {day_str}. Skipping daily summary.")
        return None

    total_duration = sum(int(r.get('duration_seconds') or 0) for r in new_rows)

    content = [
        f"# Daily Summary for {day_str}",
        "",
        "## 🔴 Failures (fail_count ≥ 2)",
    ]
    if red_rows:
        content.extend(_fail_line(r) for r in red_rows)
    else:
        content.append("(none)")
    content += [
        "",
        "## Statistics",
        f"- New Reports: {len(new_rows)}",
        f"- Reused References: {len(reused_rows)}",
        f"- Pending (Unprocessed): {len(pending_rows)}",
        f"- Total New Audio Duration: {total_duration // 3600}h {(total_duration % 3600) // 60}m {total_duration % 60}s",
        "",
        "## New Reports",
        "| Uploader / Name | Title | Report Link |",
        "| --- | --- | --- |",
    ]
    content.extend(_row_line(r) for r in new_rows) if new_rows else content.append("(none)")
    content += [
        "",
        "## Reused References (existing MD, no new upload)",
        "| Uploader / Name | Title | Report Link |",
        "| --- | --- | --- |",
    ]
    content.extend(_row_line(r) for r in reused_rows) if reused_rows else content.append("(none)")
    content += [
        "",
        "## Unprocessed (PENDING_KILLED, retried silently next run)",
    ]
    if pending_rows:
        content.extend(f"- `{_clean(r.get('video_id'))}` {_clean(r.get('url'))}" for r in pending_rows)
    else:
        content.append("(none)")

    out_dir = config.REPORT_DIR / 'daily_digest' / year_month
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_dir / f"{day_str}.md"

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
