#!/usr/bin/env python3
"""
Channel monitoring entrypoint for cron.
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, List

import yt_dlp

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import config
from src.logger import setup_logging, get_logger
from src.main import process_video

logger = setup_logging()


def read_channels(file_path: Path) -> List[str]:
    """Read channel URLs from a file."""
    if not file_path.exists():
        raise FileNotFoundError(f"Channels file not found: {file_path}")

    channels: List[str] = []
    for line in file_path.read_text(encoding='utf-8').splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith('#'):
            continue
        channels.append(cleaned)

    return channels


def parse_upload_datetime(entry: Dict) -> Optional[datetime]:
    """Parse upload datetime from a yt-dlp entry."""
    timestamp = entry.get('timestamp')
    if timestamp:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    upload_date = entry.get('upload_date')
    if upload_date:
        try:
            return datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=timezone.utc)
        except ValueError:
            logger.warning("Unrecognized upload_date format: %s", upload_date)

    return None


def get_recent_video(channel_url: str,
                     lookback_hours: int,
                     max_entries: int,
                     cookies_file: Optional[str]) -> Optional[Dict]:
    """Return the most recent video entry within the lookback window."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'playlistend': max_entries,
        'skip_download': True,
    }

    if cookies_file:
        ydl_opts['cookiefile'] = cookies_file

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)

    entries = [entry for entry in (info.get('entries') or []) if entry]
    if not entries:
        return None

    with_dates = []
    for entry in entries:
        upload_dt = parse_upload_datetime(entry)
        if upload_dt:
            with_dates.append((upload_dt, entry))

    if not with_dates:
        return None

    with_dates.sort(key=lambda item: item[0], reverse=True)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    for upload_dt, entry in with_dates:
        if upload_dt >= cutoff:
            return entry

    return None


def resolve_video_url(entry: Dict) -> Optional[str]:
    """Resolve a video URL from a yt-dlp entry."""
    for key in ('webpage_url', 'url'):
        value = entry.get(key)
        if value:
            if value.startswith('http'):
                return value
            return f"https://www.youtube.com/watch?v={value}"

    video_id = entry.get('id')
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"

    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Process latest channel uploads within the last 24 hours",
    )
    parser.add_argument(
        '--channels-file',
        type=str,
        default=str(config.CHANNELS_FILE),
        help='Path to channels list file'
    )
    parser.add_argument(
        '--style',
        choices=['brief', 'detailed'],
        default='detailed',
        help='Summary style'
    )
    parser.add_argument(
        '--upload',
        action='store_true',
        help='Upload report files to GitHub repository'
    )
    parser.add_argument(
        '--keep-audio',
        action='store_true',
        help='Keep downloaded audio files'
    )
    parser.add_argument(
        '--lookback-hours',
        type=int,
        default=24,
        help='Lookback window in hours'
    )
    parser.add_argument(
        '--max-entries',
        type=int,
        default=8,
        help='Number of channel entries to inspect'
    )
    parser.add_argument(
        '--cookies',
        type=str,
        default=None,
        help='Path to cookies.txt file'
    )

    args = parser.parse_args()

    channels_file = Path(args.channels_file)
    try:
        channels = read_channels(channels_file)
    except FileNotFoundError as exc:
        logger.error(str(exc))
        return 1

    if not channels:
        logger.info("No channels found in %s", channels_file)
        return 0

    cookies_file = args.cookies
    if not cookies_file and config.USE_COOKIES_FILE:
        cookies_path = Path(config.COOKIES_FILE)
        if cookies_path.exists():
            cookies_file = str(cookies_path)

    processed = 0
    skipped = 0

    for channel_url in channels:
        logger.info("Checking channel: %s", channel_url)
        try:
            entry = get_recent_video(
                channel_url,
                lookback_hours=args.lookback_hours,
                max_entries=args.max_entries,
                cookies_file=cookies_file
            )
        except Exception as exc:
            logger.warning("Failed to fetch channel info: %s", exc)
            skipped += 1
            continue

        if not entry:
            logger.info("No uploads within last %s hours.", args.lookback_hours)
            skipped += 1
            continue

        video_url = resolve_video_url(entry)
        if not video_url:
            logger.warning("Could not resolve video URL for channel %s", channel_url)
            skipped += 1
            continue

        logger.info("Processing recent upload: %s", video_url)
        try:
            process_video(
                video_url,
                cookies_file=cookies_file,
                keep_audio=args.keep_audio,
                summary_style=args.style,
                upload_to_github_repo=args.upload
            )
            processed += 1
        except Exception as exc:
            logger.warning("Failed to process video %s: %s", video_url, exc)
            skipped += 1

    logger.info("Channel cron complete. Processed: %s, Skipped: %s", processed, skipped)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
