import logging
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

from config import config
from src.run_tracker import get_tracker
from src.youtube_handler import build_ydl_opts, _run_ydl_with_cookie_fallback
from src.pipeline import ProcessingPipeline

logger = logging.getLogger(__name__)

class ChannelWatcher:
    """Watch YouTube channels for new videos, process them, and maintain state."""

    def __init__(self, cookies_file=None, cookies_from_browser=True, browser="chrome"):
        self.tracker = get_tracker()
        self.cookies_file = cookies_file
        self.cookies_from_browser = cookies_from_browser
        self.browser = browser

    def import_watchlist(self, file_path: Path):
        """Import channel URLs from a text file into watch_channels."""
        if not file_path.exists():
            logger.error(f"Watchlist file not found: {file_path}")
            return
            
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            
        now = datetime.now()
        added = 0
        with sqlite3.connect(self.tracker.db_path) as conn:
            cursor = conn.cursor()
            for url in lines:
                import re
                m = re.search(r'youtube\.com/(@[\w.-]+|channel/[\w.-]+|c/[\w.-]+)', url)
                if not m:
                    logger.warning(f"Could not parse valid channel out of {url}")
                    continue
                channel_id = m.group(1)
                
                cursor.execute(
                    "INSERT OR IGNORE INTO watch_channels (channel_id, name, added_at) VALUES (?, ?, ?)",
                    (channel_id, url, now)
                )
                if cursor.rowcount > 0:
                    cursor.execute(
                        "INSERT OR IGNORE INTO watch_channel_state (channel_id, last_scan_time) VALUES (?, ?)",
                        (channel_id, datetime(2000, 1, 1))
                    )
                    added += 1
            conn.commit()
        logger.info(f"Imported {added} new channels from {file_path}")

    def list_watch_channels(self):
        with sqlite3.connect(self.tracker.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.channel_id, c.is_active, s.last_seen_upload_date, s.videos_processed_total 
                FROM watch_channels c 
                LEFT JOIN watch_channel_state s ON c.channel_id = s.channel_id
            """)
            return [dict(r) for r in cursor.fetchall()]

    def execute_scan(self, upload: bool = True) -> int:
        """Run a single scan across all active channels."""
        now = datetime.now()
        channels = self.list_watch_channels()
        active = [c for c in channels if c.get('is_active')]
        
        if not active:
            logger.info("No active channels to watch.")
            return 0
            
        with sqlite3.connect(self.tracker.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO watch_scan_runs (scan_start, status) VALUES (?, 'RUNNING')",
                (now,)
            )
            conn.commit()
            scan_id = cursor.lastrowid
            
        total_new_videos = 0
        total_processed = 0
        errors = 0
        
        from src.transcriber import Transcriber
        try:
            shared_transcriber = Transcriber()
        except Exception:
            shared_transcriber = None
            
        for ch in active:
            channel_id = ch['channel_id']
            last_date = ch.get('last_seen_upload_date') or "00000000"
            last_vid = ch.get('last_seen_video_id')
            
            logger.info(f"Scanning channel {channel_id} (last_date={last_date})")
            try:
                url = f"https://www.youtube.com/{channel_id}/videos"
                ydl_opts = build_ydl_opts(
                    cookies_file=self.cookies_file,
                    cookies_from_browser=self.cookies_from_browser,
                    browser=self.browser,
                    overrides={"extract_flat": True, "playlistend": 15}
                )
                
                res = _run_ydl_with_cookie_fallback(
                    cookies_file=self.cookies_file,
                    cookies_from_browser=self.cookies_from_browser,
                    browser=self.browser,
                    ydl_opts=ydl_opts,
                    context=f"Scanning {channel_id}",
                    action=lambda ydl: ydl.extract_info(url, download=False)
                )
                
                entries = res.get('entries', [])
                new_videos = []
                
                for entry in entries:
                    vid = entry.get('id')
                    with sqlite3.connect(self.tracker.db_path) as conn:
                        cur = conn.cursor()
                        cur.execute("SELECT id, status FROM runs WHERE identifier = ?", (vid,))
                        row = cur.fetchone()
                        
                    if not row or row[1] != 'COMPLETED':
                        new_videos.append(vid)
                    elif vid == last_vid:
                        break
                        
                new_videos.reverse()
                for vid in new_videos:
                    total_new_videos += 1
                    logger.info(f"Processing video from {channel_id}: {vid}")
                    pipe = ProcessingPipeline(
                        run_type='youtube',
                        url_or_path=f"https://www.youtube.com/watch?v={vid}",
                        identifier=vid,
                        summary_style='detailed',
                        upload=upload,
                        transcriber=shared_transcriber
                    )
                    
                    try:
                        res_pipe = pipe.run_youtube(
                            cookies_file=self.cookies_file,
                            cookies_from_browser=self.cookies_from_browser,
                            browser=self.browser,
                            keep_audio=False
                        )
                        vinfo = res_pipe.get('video_info', {})
                        up_date = vinfo.get('upload_date', '00000000')
                        
                        if up_date >= last_date:
                            last_date = up_date
                            last_vid = vid
                            
                        total_processed += 1
                    except Exception as e:
                        logger.error(f"Error processing video {vid}: {e}")
                        errors += 1
                
                with sqlite3.connect(self.tracker.db_path) as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE watch_channel_state 
                        SET last_scan_time = ?, last_seen_upload_date = ?, last_seen_video_id = ?,
                            videos_processed_total = videos_processed_total + ?
                        WHERE channel_id = ?
                    """, (datetime.now(), last_date, last_vid, len(new_videos), channel_id))
                    conn.commit()

            except Exception as e:
                logger.error(f"Failed scanning channel {channel_id}: {e}")
                errors += 1
                
        with sqlite3.connect(self.tracker.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE watch_scan_runs 
                SET scan_end = ?, channels_scanned = ?, new_videos_found = ?, videos_processed = ?, errors_count = ?, status = 'COMPLETED'
                WHERE id = ?
            """, (datetime.now(), len(active), total_new_videos, total_processed, errors, scan_id))
            conn.commit()
            
        from src.daily_summary import generate_daily_summary
        try:
            generate_daily_summary(upload=upload)
        except Exception as e:
            logger.error(f"Daily summary failed after scan: {e}")

        return total_processed
