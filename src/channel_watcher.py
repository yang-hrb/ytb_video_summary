import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Callable

from config import config
from src.run_tracker import get_tracker, get_dedup_db, mark_video_pending_killed
from src.youtube_handler import build_ydl_opts, _run_ydl_with_cookie_fallback
from src.pipeline import ProcessingPipeline

logger = logging.getLogger(__name__)

# Spec §5: only videos published in the last N days are in scope.
SCAN_WINDOW_DAYS = 2

CHANNELLIST_EXAMPLE = """# Channel watchlist — one channel URL per line.
# Blank lines and lines starting with # are skipped. This file is hand-maintained.
# --scan only picks up videos published in the last 2 days.
# Examples (uncomment and replace with channels you follow):
# https://www.youtube.com/@SomeChannel
# https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx
"""


def read_channellist(path) -> List[str]:
    """Read channel URLs from a text file, skipping blanks and # comments.

    Creates an example file and returns [] when the path does not exist.
    """
    p = Path(path)
    if not p.exists():
        p.write_text(CHANNELLIST_EXAMPLE, encoding="utf-8")
        logger.info("Created example channellist: %s", p)
        return []
    channels = []
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            channels.append(s)
    return channels


SCAN_LOCK_NAME = "scan.lock"
# A lock older than this is considered stale (previous run died without cleanup).
SCAN_LOCK_STALE_HOURS = 6


def acquire_scan_lock(lock_path=None, stale_hours: float = SCAN_LOCK_STALE_HOURS) -> Optional[Path]:
    """Single-instance guard for --scan (stdlib Path lock file, no new deps).

    Returns the lock path on success, None when another scan holds a fresh lock.
    """
    p = Path(lock_path) if lock_path else config.LOG_DIR / SCAN_LOCK_NAME
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        p.touch(exist_ok=False)
        return p
    except FileExistsError:
        try:
            age_h = (time.time() - p.stat().st_mtime) / 3600
        except OSError:
            return None
        if age_h < stale_hours:
            return None
        logger.warning("Removing stale scan lock (age %.1fh): %s", age_h, p)
        try:
            p.unlink()
        except OSError:
            return None
        try:
            p.touch(exist_ok=False)
            return p
        except FileExistsError:
            return None


def _mark_pending_killed(dedup_db, video_id: str, pending_now: List[Dict]):
    """Timeout bookkeeping: NOT a failure — fail_count untouched, silent retry next scan."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    mark_video_pending_killed(dedup_db, video_id, url)
    row = dedup_db.execute_one("SELECT * FROM videos WHERE video_id = ?", (video_id,))
    if row:
        pending_now.append(row)
    logger.warning("Time budget exceeded; %s marked PENDING_KILLED (no fail_count bump).", video_id)


def entry_publish_date(entry: Dict) -> Optional[str]:
    """Best-effort publish date as YYYYMMDD, or None when unavailable.

    Prefers flat-extract `upload_date`; falls back to `timestamp`, then
    `published_parsed`. No date means "old" (never auto-run).
    """
    d = entry.get("upload_date")
    if d and len(str(d)) == 8 and str(d).isdigit():
        return str(d)
    ts = entry.get("timestamp")
    if ts:
        try:
            return datetime.fromtimestamp(float(ts)).strftime("%Y%m%d")
        except (ValueError, TypeError, OSError, OverflowError):
            pass
    pp = entry.get("published_parsed")
    if pp:
        try:
            return datetime(*pp[:6]).strftime("%Y%m%d")
        except (ValueError, TypeError):
            pass
    return None


def is_recent(entry: Dict, cutoff_yyyymmdd: str) -> bool:
    """True only when the entry has a known date inside the scan window."""
    d = entry_publish_date(entry)
    return d is not None and d >= cutoff_yyyymmdd


def select_scan_videos(
    entries: Optional[List[Dict]],
    status_of: Callable[[str], Optional[str]],
    cutoff_yyyymmdd: str,
) -> Tuple[List[Dict], List[str]]:
    """Split flat-extract entries (newest-first) into (to_process, failed).

    - First COMPLETED entry truncates the walk (cursor: everything older
      was already seen in a previous scan).
    - First old/undated entry truncates too (older entries can only be older).
    - FAILED entries are collected separately and never auto-run.
    """
    to_process: List[Dict] = []
    failed: List[str] = []
    for entry in entries or []:
        if not entry:
            continue
        vid = entry.get("id")
        if not vid:
            continue
        status = status_of(vid)
        if status == "COMPLETED":
            break
        if not is_recent(entry, cutoff_yyyymmdd):
            break
        if status == "FAILED":
            failed.append(vid)
            continue
        to_process.append(entry)
    return to_process, failed


class ChannelWatcher:
    """Watch YouTube channels for new videos, process them, and maintain state."""

    def __init__(self, cookies_file=None, cookies_from_browser=True, browser="chrome"):
        self.tracker = get_tracker()
        self.cookies_file = cookies_file
        self.cookies_from_browser = cookies_from_browser
        self.browser = browser

    def import_watchlist(self, file_path: Path):
        """Import channel URLs from a text file into watch_channels."""
        import re

        urls = read_channellist(file_path)
        if not urls and not Path(file_path).exists():
            return
        now = datetime.now()
        added = 0
        for url in urls:
            m = re.search(r'youtube\.com/(@[\w.-]+|channel/[\w.-]+|c/[\w.-]+)', url)
            if not m:
                logger.warning(f"Could not parse valid channel out of {url}")
                continue
            channel_id = m.group(1)
            rowcount = self.tracker.db.execute_update(
                "INSERT OR IGNORE INTO watch_channels (channel_id, name, added_at) VALUES (?, ?, ?)",
                (channel_id, url, now),
            )
            if rowcount > 0:
                self.tracker.db.execute_update(
                    "INSERT OR IGNORE INTO watch_channel_state (channel_id, last_scan_time) VALUES (?, ?)",
                    (channel_id, datetime(2000, 1, 1)),
                )
                added += 1
        logger.info(f"Imported {added} new channels from {file_path}")

    def list_watch_channels(self):
        return self.tracker.db.execute("""
            SELECT c.channel_id, c.is_active, s.last_seen_upload_date, s.videos_processed_total
            FROM watch_channels c
            LEFT JOIN watch_channel_state s ON c.channel_id = s.channel_id
        """)

    def fetch_channel_entries(self, channel_url: str, cutoff_yyyymmdd: str) -> List[Dict]:
        """Flat-extract a channel's /videos feed. 2-day window via dateafter + client filter."""
        feed_url = channel_url.rstrip("/")
        if not feed_url.endswith("/videos"):
            feed_url += "/videos"
        ydl_opts = build_ydl_opts(
            cookies_file=self.cookies_file,
            cookies_from_browser=self.cookies_from_browser,
            browser=self.browser,
            overrides={"extract_flat": True, "dateafter": cutoff_yyyymmdd},
        )
        res = _run_ydl_with_cookie_fallback(
            cookies_file=self.cookies_file,
            cookies_from_browser=self.cookies_from_browser,
            browser=self.browser,
            ydl_opts=ydl_opts,
            context=f"Scanning {channel_url}",
            action=lambda ydl: ydl.extract_info(feed_url, download=False),
        )
        return res.get('entries', []) or []

    def execute_scan(
        self,
        channels_file=None,
        upload: bool = True,
        summary_style: str = "detailed",
        max_hours: Optional[float] = None,
    ) -> int:
        """Run a single scan. channels_file mode reads channellist.txt directly;
        without it, falls back to the legacy watch_channels table.

        The digest date is this scan's start day (spec §6.1): even if the run
        spills past midnight, everything lands in that one digest file.

        max_hours (spec §5): in-process time budget via time.monotonic. When the
        deadline hits, undispatched videos are marked PENDING_KILLED (fail_count
        untouched — a timeout is "never ran", silently retried next scan) and a
        partial digest is still emitted. No APScheduler, no system timeout.
        """
        now = datetime.now()
        digest_date = now.strftime("%Y%m%d")
        cutoff = (now - timedelta(days=SCAN_WINDOW_DAYS)).strftime("%Y%m%d")

        legacy_state = {}
        if channels_file is not None:
            channel_urls = read_channellist(channels_file)
        else:
            rows = self.list_watch_channels()
            active = [c for c in rows if c.get('is_active')]
            channel_urls = [f"https://www.youtube.com/{c['channel_id']}/videos" for c in active]
            legacy_state = {c['channel_id']: c for c in active}

        if not channel_urls:
            logger.info("No channels to watch.")
            return 0

        dedup_db = get_dedup_db()

        deadline = time.monotonic() + max_hours * 3600 if max_hours is not None else None

        from src.batch import _make_shared_transcriber
        try:
            shared_transcriber = _make_shared_transcriber()
        except Exception:
            logger.warning("Transcriber prewarm failed; pipelines will lazy-load.", exc_info=True)
            shared_transcriber = None

        scan_id = self.tracker.db.execute_insert(
            "INSERT INTO watch_scan_runs (scan_start, status) VALUES (?, 'RUNNING')",
            (now,),
        )

        total_new_videos = 0
        total_processed = 0
        errors = 0
        new_now: List[Dict] = []
        reused_now: List[Dict] = []
        pending_now: List[Dict] = []
        timed_out = False

        for channel_url in channel_urls:
            if timed_out:
                break
            logger.info(f"Scanning channel {channel_url} (cutoff={cutoff})")
            try:
                entries = self.fetch_channel_entries(channel_url, cutoff)
            except Exception as e:
                logger.error(f"Failed scanning channel {channel_url}: {e}")
                errors += 1
                continue

            ids = [e.get('id') for e in entries or [] if e and e.get('id')]
            status_map = {}
            if ids:
                placeholders = ",".join("?" for _ in ids)
                for r in dedup_db.execute(
                    f"SELECT video_id, status FROM videos WHERE video_id IN ({placeholders})",
                    tuple(ids),
                ):
                    status_map[r['video_id']] = r['status']

            to_process, failed = select_scan_videos(entries, status_map.get, cutoff)
            if failed:
                logger.warning(
                    "Channel %s: %d recent video(s) previously FAILED, not auto-running: %s",
                    channel_url, len(failed), ", ".join(failed),
                )

            queue = list(reversed(to_process))
            for i, entry in enumerate(queue):
                vid = entry['id']
                if deadline is not None and time.monotonic() >= deadline:
                    timed_out = True
                    for rest in queue[i:]:
                        _mark_pending_killed(dedup_db, rest['id'], pending_now)
                    break
                total_new_videos += 1
                logger.info(f"Processing video from {channel_url}: {vid}")
                pipe = ProcessingPipeline(
                    run_type='youtube',
                    url_or_path=f"https://www.youtube.com/watch?v={vid}",
                    identifier=vid,
                    summary_style=summary_style,
                    upload=upload,
                    transcriber=shared_transcriber,
                )
                try:
                    res = pipe.run_youtube(
                        cookies_file=self.cookies_file,
                        cookies_from_browser=self.cookies_from_browser,
                        browser=self.browser,
                        keep_audio=False,
                    )
                    total_processed += 1
                    row = dedup_db.execute_one(
                        "SELECT * FROM videos WHERE video_id = ?", (vid,))
                    if row:
                        (reused_now if res.get('reused') else new_now).append(row)
                except Exception as e:
                    logger.error(f"Error processing video {vid}: {e}")
                    errors += 1

            if legacy_state:
                key = channel_url.rsplit("youtube.com/", 1)[-1].rsplit("/videos", 1)[0]
                if key in legacy_state:
                    self.tracker.db.execute_update(
                        """UPDATE watch_channel_state
                           SET last_scan_time = ?, videos_processed_total = videos_processed_total + ?
                           WHERE channel_id = ?""",
                        (datetime.now(), len(to_process), key),
                    )

        self.tracker.db.execute_update(
            """UPDATE watch_scan_runs
               SET scan_end = ?, channels_scanned = ?, new_videos_found = ?,
                   videos_processed = ?, errors_count = ?, status = 'COMPLETED'
               WHERE id = ?""",
            (datetime.now(), len(channel_urls), total_new_videos, total_processed, errors, scan_id),
        )

        from src.daily_summary import generate_daily_summary
        try:
            generate_daily_summary(target_date=digest_date, upload=upload,
                                   run_results={'new': new_now, 'reused': reused_now,
                                                'pending': pending_now})
        except Exception as e:
            logger.error(f"Daily summary failed after scan: {e}")

        return total_processed
