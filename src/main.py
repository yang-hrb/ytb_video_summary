#!/usr/bin/env python3
"""
Audio/Video Transcription & Summarization Tool - Main Program
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from colorama import init, Fore, Style

# Ensure project root is on sys.path so imports work whether the user runs
# `python src/main.py` or `python -m src.main` from the repository root.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import config
from src.logger import setup_logging, get_logger, get_current_log_file
from src.youtube_handler import process_youtube_video, get_playlist_videos
from src.apple_podcasts_handler import process_apple_podcast_episode, get_podcast_episodes
from src.transcriber import transcribe_video_audio, read_subtitle_file, Transcriber
from src.summarizer import summarize_transcript
from src.utils import get_file_size_mb, is_playlist_url, extract_playlist_id, sanitize_filename, is_apple_podcasts_url
from src.github_handler import upload_to_github, upload_logs_to_github
from src.run_tracker import get_tracker, log_failure
from src.batch import (
    process_playlist_batch,
    process_local_folder_batch,
    process_podcast_show_batch,
    process_batch_file as _process_batch_file,
)
from src.pipeline import ProcessingPipeline, STAGE_TO_FAILED_STATUS

# Initialize colorama
init(autoreset=True)

# Initialize logging system
logger = setup_logging()


def print_banner():
    """Print program banner"""
    banner = f"""
{Fore.CYAN}╔═══════════════════════════════════════════════════════════╗
║   Audio/Video Transcript & Summarizer v2.1                ║
║   YouTube + Apple Podcasts + Local MP3                    ║
╚═══════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    # Print banner to console (not logged to file)
    print(banner)


def log_step(step: str, description: str):
    """Log step information"""
    logger.info(f"[{step}] {description}")


def log_error(message: str):
    """Log error message"""
    logger.error(message)


def log_success(message: str):
    """Log success message"""
    logger.info(f"SUCCESS: {message}")


def process_video(
    url: str,
    cookies_file: Optional[str] = None,
    cookies_from_browser: bool = True,
    browser: str = "chrome",
    keep_audio: bool = False,
    summary_style: str = "detailed",
    upload_to_github_repo: bool = False
) -> dict:
    """
    Process a single video through the complete pipeline.

    Uses ProcessingPipeline internally for accurate per-stage status tracking.
    """
    pipeline = ProcessingPipeline(
        run_type='youtube',
        url_or_path=url,
        identifier='',           # filled after download inside run_youtube()
        summary_style=summary_style,
        upload=upload_to_github_repo,
    )
    return pipeline.run_youtube(
        cookies_file=cookies_file,
        cookies_from_browser=cookies_from_browser,
        browser=browser,
        keep_audio=keep_audio,
    )


def process_local_mp3(
    mp3_path: Path,
    summary_style: str = "detailed",
    upload_to_github_repo: bool = False
) -> dict:
    """
    Process a local MP3 file through the complete pipeline.

    Uses ProcessingPipeline internally for accurate per-stage status tracking.
    """
    pipeline = ProcessingPipeline(
        run_type='local',
        url_or_path=str(mp3_path),
        identifier=mp3_path.stem,
        summary_style=summary_style,
        upload=upload_to_github_repo,
    )
    return pipeline.run_local_mp3(mp3_path)


def process_local_folder(
    folder_path: Path,
    summary_style: str = "detailed",
    upload_to_github_repo: bool = False
) -> list:
    """Process all MP3 files in a local folder (delegates to batch module)."""
    return process_local_folder_batch(
        folder_path, summary_style=summary_style, upload=upload_to_github_repo
    )


def process_playlist(
    playlist_url: str,
    cookies_file: Optional[str] = None,
    cookies_from_browser: bool = True,
    browser: str = "chrome",
    keep_audio: bool = False,
    summary_style: str = "detailed",
    upload_to_github_repo: bool = False
) -> list:
    """Process all videos in a playlist (delegates to batch module)."""
    return process_playlist_batch(
        playlist_url,
        cookies_file=cookies_file,
        cookies_from_browser=cookies_from_browser,
        browser=browser,
        keep_audio=keep_audio,
        summary_style=summary_style,
        upload=upload_to_github_repo,
    )


def process_apple_podcast(
    url: str,
    episode_index: int = 0,
    summary_style: str = "detailed",
    upload_to_github_repo: bool = False
) -> dict:
    """
    Process a single Apple Podcasts episode through the complete pipeline.

    Uses ProcessingPipeline internally for accurate per-stage status tracking.
    """
    log_step("1/3", "Fetching podcast episode information...")
    result = process_apple_podcast_episode(url, episode_index)

    podcast_info = result['podcast_info']
    episode_info = result['episode_info']
    audio_path = result['audio_path']
    identifier = result['identifier']

    logger.info("  Podcast: %s", podcast_info['title'])
    logger.info("  Episode: %s", episode_info['title'])

    video_info = {
        'title': episode_info['title'],
        'uploader': podcast_info.get('artist', podcast_info.get('title', 'Unknown Podcast')),
        'duration': episode_info.get('duration', 0),
    }

    pipeline = ProcessingPipeline(
        run_type='podcast',
        url_or_path=url,
        identifier=identifier,
        summary_style=summary_style,
        upload=upload_to_github_repo,
    )
    inner = pipeline.run_podcast(audio_path, video_info)

    return {
        'identifier': identifier,
        'podcast_info': podcast_info,
        'episode_info': episode_info,
        **inner,
    }


def process_apple_podcast_show(
    url: str,
    summary_style: str = "detailed",
    upload_to_github_repo: bool = False
) -> list:
    """Process all episodes from an Apple Podcasts show (delegates to batch module)."""
    return process_podcast_show_batch(
        url, summary_style=summary_style, upload=upload_to_github_repo
    )


def detect_input_type(line: str) -> str:
    """
    Detect the type of input from a line

    Args:
        line: Input line from batch file

    Returns:
        Input type: 'youtube_video', 'youtube_playlist', 'apple_podcast', 'local_folder', or 'unknown'
    """
    line = line.strip()

    # Check if it's a URL
    if line.startswith('http://') or line.startswith('https://'):
        if is_apple_podcasts_url(line):
            return 'apple_podcast'
        elif is_playlist_url(line):
            return 'youtube_playlist'
        else:
            # Assume it's a YouTube video URL
            return 'youtube_video'
    else:
        # Check if it's a local path
        path = Path(line)
        if path.exists() and path.is_dir():
            return 'local_folder'

    return 'unknown'


def process_batch_file(
    batch_file: Path,
    cookies_file: Optional[str] = None,
    cookies_from_browser: bool = True,
    browser: str = "chrome",
    keep_audio: bool = False,
    summary_style: str = "detailed",
    upload_to_github_repo: bool = False
) -> dict:
    """
    Process multiple inputs from a batch file

    Batch file format:
    - Each line contains one input (YouTube URL, Apple Podcast URL, or local MP3 folder path)
    - Empty lines are ignored
    - Lines starting with # are treated as comments and ignored

    Args:
        batch_file: Path to batch input file
        cookies_file: Path to cookies.txt file (for YouTube)
        cookies_from_browser: Prefer browser session cookies when available
        browser: Browser name for cookiesfrombrowser (default: chrome)
        keep_audio: Whether to keep downloaded audio files (for YouTube)
        summary_style: Summary style (brief/detailed)
        upload_to_github_repo: Whether to upload reports to GitHub

    Returns:
        Dictionary containing processing statistics and results
    """
    try:
        log_step("Batch", "Reading batch input file...")

        if not batch_file.exists():
            log_error(f"Batch file does not exist: {batch_file}")
            return {'success': False, 'error': 'File not found'}

        # Read all lines from file
        with open(batch_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Filter out empty lines and comments
        inputs = []
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line and not line.startswith('#'):
                inputs.append((i, line))

        if not inputs:
            log_error("No valid inputs found in batch file")
            return {'success': False, 'error': 'No valid inputs'}

        logger.info(f"Found {len(inputs)} inputs to process")
        logger.info("="*60)

        # Process each input
        results = {
            'total': len(inputs),
            'processed': 0,
            'failed': 0,
            'items': []
        }

        for idx, (line_num, input_line) in enumerate(inputs, 1):
            logger.info("")
            logger.info("="*60)
            logger.info(f"Processing input [{idx}/{len(inputs)}] (line {line_num})")
            logger.info(f"Input: {input_line}")
            logger.info("="*60)

            # Detect input type
            input_type = detect_input_type(input_line)
            logger.info(f"Detected type: {input_type}")

            item_result = {
                'line_number': line_num,
                'input': input_line,
                'type': input_type,
                'success': False,
                'error': None
            }

            try:
                if input_type == 'youtube_video':
                    result = process_video(
                        input_line,
                        cookies_file=cookies_file,
                        cookies_from_browser=cookies_from_browser,
                        browser=browser,
                        keep_audio=keep_audio,
                        summary_style=summary_style,
                        upload_to_github_repo=upload_to_github_repo
                    )
                    item_result['success'] = True
                    item_result['result'] = result
                    results['processed'] += 1

                elif input_type == 'youtube_playlist':
                    result = process_playlist(
                        input_line,
                        cookies_file=cookies_file,
                        cookies_from_browser=cookies_from_browser,
                        browser=browser,
                        keep_audio=keep_audio,
                        summary_style=summary_style,
                        upload_to_github_repo=upload_to_github_repo
                    )
                    item_result['success'] = True
                    item_result['result'] = result
                    results['processed'] += 1

                elif input_type == 'apple_podcast':
                    result = process_apple_podcast(
                        input_line,
                        episode_index=0,  # Latest episode
                        summary_style=summary_style,
                        upload_to_github_repo=upload_to_github_repo
                    )
                    item_result['success'] = True
                    item_result['result'] = result
                    results['processed'] += 1

                elif input_type == 'local_folder':
                    folder_path = Path(input_line)
                    result = process_local_folder(
                        folder_path,
                        summary_style=summary_style,
                        upload_to_github_repo=upload_to_github_repo
                    )
                    item_result['success'] = True
                    item_result['result'] = result
                    results['processed'] += 1

                else:
                    error_msg = f"Unknown input type: {input_line}"
                    log_error(error_msg)
                    item_result['error'] = error_msg
                    results['failed'] += 1

            except Exception as e:
                error_msg = str(e)
                log_error(f"Failed to process input: {error_msg}")
                logger.debug("Error processing line %s", line_num, exc_info=True)
                item_result['error'] = error_msg
                results['failed'] += 1

            results['items'].append(item_result)

        # Output summary
        logger.info("")
        logger.info("="*60)
        logger.info("BATCH PROCESSING COMPLETE")
        logger.info("="*60)
        logger.info(f"Total inputs: {results['total']}")
        logger.info(f"Successfully processed: {results['processed']}")
        logger.info(f"Failed: {results['failed']}")

        if results['failed'] > 0:
            logger.warning("")
            logger.warning("Failed inputs:")
            for item in results['items']:
                if not item['success']:
                    logger.warning(f"  Line {item['line_number']}: {item['input']}")
                    logger.warning(f"    Error: {item['error']}")

        results['success'] = True
        return results

    except Exception as e:
        log_error(f"Batch processing failed: {e}")
        logger.debug("Error in batch processing", exc_info=True)
        return {'success': False, 'error': str(e)}



def process_resume_only(summary_style: str = "detailed", upload: bool = False) -> dict:
    """Resume all stalled runs using the smart stage-based strategy."""
    tracker = get_tracker()
    resumable_runs = tracker.get_resumable_runs()

    results = {"total": len(resumable_runs), "processed": 0, "failed": 0}

    if not resumable_runs:
        logger.info("No resumable runs found.")
        return results

    logger.info("Found %d resumable run(s)", len(resumable_runs))

    for run in resumable_runs:
        res = ProcessingPipeline.resume(run, summary_style=summary_style, upload=upload)
        if res.get('success'):
            results['processed'] += 1
            logger.info("Resumed run %s successfully", run['id'])
        elif res.get('skipped'):
            logger.info("Skipped run %s (not resumable)", run['id'])
        else:
            results['failed'] += 1
            logger.error("Resume failed for run %s: %s", run['id'], res.get('error'))

    return results


def print_status():
    """Print processing statistics (--status CLI command)."""
    tracker = get_tracker()
    stats = tracker.get_stats()
    print("\n📊 Processing Statistics")
    print("=" * 40)
    print(f"  Total runs: {stats['total']}")
    print("\nBy status:")
    for status, count in sorted(stats['by_status'].items()):
        print(f"  {status:<25} {count}")
    print("\nBy type:")
    for run_type, count in sorted(stats['by_type'].items()):
        print(f"  {run_type:<25} {count}")
    print()


def print_failed_runs():
    """Print failed runs with stage and error details (--list-failed)."""
    tracker = get_tracker()
    runs = tracker.get_failed_runs()
    if not runs:
        print("\nNo failed runs found.")
        return
    print(f"\n❌ Failed runs ({len(runs)})")
    print("=" * 60)
    for r in runs:
        print(f"  id={r['id']} | status={r['status']} | stage={r.get('stage','?')}")
        print(f"    identifier : {r['identifier']}")
        print(f"    url/path   : {r['url_or_path']}")
        print(f"    error      : {r.get('error_message', '')[:120]}")
        print(f"    updated_at : {r['updated_at']}")
        print()


def print_resumable_runs():
    """Print resumable runs (--list-resumable)."""
    tracker = get_tracker()
    runs = tracker.get_resumable_runs()
    if not runs:
        print("\nNo resumable runs found.")
        return
    print(f"\n🔄 Resumable runs ({len(runs)})")
    print("=" * 60)
    for r in runs:
        resume_stage = tracker.RESUMABLE_STATUS_MAP.get(r['status'], '?')
        print(f"  id={r['id']} | status={r['status']} → resume from: {resume_stage}")
        print(f"    identifier : {r['identifier']}")
        print(f"    updated_at : {r['updated_at']}")
        print()

def main():
    """Main function - CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Audio/Video Transcription & Summarization Tool - Supports YouTube, Apple Podcasts, and Local MP3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single YouTube video (default)
  python src/main.py "https://youtube.com/watch?v=xxxxx"
  python src/main.py -video "https://youtube.com/watch?v=xxxxx" --style brief

  # Process YouTube playlist
  python src/main.py -list "https://youtube.com/playlist?list=xxxxx"
  python src/main.py -list "https://youtube.com/watch?v=xxxxx&list=xxxxx"

  # Process single Apple Podcasts episode (latest)
  python src/main.py --apple-podcast-single "https://podcasts.apple.com/us/podcast/podcast-name/id123456789"

  # Process all episodes from Apple Podcasts show
  python src/main.py --apple-podcast-list "https://podcasts.apple.com/us/podcast/podcast-name/id123456789"

  # Process local MP3 folder
  python src/main.py -local /path/to/mp3/folder
  python src/main.py -local ./audio_files --style detailed

  # Process batch input file (mix of URLs and paths)
  python src/main.py --batch input.txt
  python src/main.py --batch input.txt --style brief --upload
        """
    )

    # Create mutually exclusive group: -video, -list, -local, --apple-podcast-single, --apple-podcast-list (choose one)
    input_group = parser.add_mutually_exclusive_group()

    input_group.add_argument(
        '-video',
        type=str,
        metavar='URL',
        help='YouTube video URL'
    )

    input_group.add_argument(
        '-list',
        type=str,
        metavar='URL',
        help='YouTube playlist URL'
    )

    input_group.add_argument(
        '--apple-podcast-single',
        type=str,
        metavar='URL',
        help='Apple Podcasts URL (process latest episode only)'
    )

    input_group.add_argument(
        '--apple-podcast-list',
        type=str,
        metavar='URL',
        help='Apple Podcasts URL (process all episodes from show)'
    )

    input_group.add_argument(
        '-local',
        type=str,
        metavar='PATH',
        help='Local MP3 folder path'
    )

    input_group.add_argument(
        '--batch',
        type=str,
        metavar='FILE',
        help='Batch input file (one URL or path per line)'
    )

    # Diagnostic commands (Phase 2.5)
    diag_group = parser.add_argument_group('diagnostics')
    diag_group.add_argument(
        '--status',
        action='store_true',
        help='Display processing statistics and exit'
    )
    diag_group.add_argument(
        '--list-failed',
        action='store_true',
        help='List failed runs with stage/error details and exit'
    )
    diag_group.add_argument(
        '--list-resumable',
        action='store_true',
        help='List all resumable runs and exit'
    )

    # Keep positional argument for backward compatibility
    parser.add_argument(
        'url',
        nargs='?',
        help='YouTube video or playlist URL (default mode)'
    )

    parser.add_argument(
        '--cookies',
        type=str,
        help='Path to cookies.txt file (fallback only; browser cookies are preferred)'
    )

    parser.add_argument(
        '--cookies-from-browser',
        action=argparse.BooleanOptionalAction,
        default=False,
        help='Use cookies from local browser profile (default: disabled; use --cookies-from-browser to enable)'
    )

    parser.add_argument(
        '--browser',
        choices=['chrome', 'edge', 'firefox'],
        default='chrome',
        help='Browser profile to read cookies from (default: chrome)'
    )

    parser.add_argument(
        '--keep-audio',
        action='store_true',
        help='Keep downloaded audio files (YouTube only)'
    )

    parser.add_argument(
        '--style',
        choices=['brief', 'detailed'],
        default='detailed',
        help='Summary style: brief or detailed'
    )

    parser.add_argument(
        '--resume-only',
        action='store_true',
        help='Resume summaries for runs in TRANSCRIPT_GENERATED or SUMMARY_FAILED status'
    )

    parser.add_argument(
        '--upload',
        action='store_true',
        help='Upload report files to GitHub repository'
    )

    watcher_group = parser.add_argument_group('watcher')
    watcher_group.add_argument('--import-watchlist', type=str, metavar='FILE', help='Import channel URLs from text file into watchlist')
    watcher_group.add_argument('--list-watch-channels', action='store_true', help='List currently monitored channels')
    watcher_group.add_argument('--watch-run-once', action='store_true', help='Execute a single watch scan across all active channels')
    watcher_group.add_argument('--watch-daemon', action='store_true', help='Run the watcher continuously (daemon mode)')
    watcher_group.add_argument('--watch-time', type=str, help='Interval for daemon execution (seconds)')

    summary_group = parser.add_argument_group('summary')
    summary_group.add_argument('--daily-summary', type=str, nargs='?', const='today', metavar='DATE', help='Generate daily summary (optional format: YYYYMMDD)')

    args = parser.parse_args()

    # Print banner
    print_banner()

    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        log_error(str(e))
        logger.error("Please ensure OPENROUTER_API_KEY is set in .env file")
        sys.exit(1)

    # Determine processing mode
    try:
        # --- Diagnostic commands (Phase 2.5) ---
        if args.status:
            print_status()
            sys.exit(0)

        if args.list_failed:
            print_failed_runs()
            sys.exit(0)

        if args.list_resumable:
            print_resumable_runs()
            sys.exit(0)

        if args.resume_only:
            logger.info("Resume-only mode")
            results = process_resume_only(summary_style=args.style, upload=args.upload)

        elif args.import_watchlist:
            from src.channel_watcher import ChannelWatcher
            w = ChannelWatcher(cookies_file=args.cookies, cookies_from_browser=args.cookies_from_browser, browser=args.browser)
            w.import_watchlist(Path(args.import_watchlist))
            sys.exit(0)
            
        elif args.list_watch_channels:
            from src.channel_watcher import ChannelWatcher
            w = ChannelWatcher()
            channels = w.list_watch_channels()
            print("\n📺 Watchlist Channels")
            print("=" * 60)
            for c in channels:
                print(f"ID: {c['channel_id']} | Active: {c['is_active']} | Last seen: {c['last_seen_upload_date']} | Total processed: {c['videos_processed_total']}")
            sys.exit(0)
            
        elif args.watch_run_once:
            logger.info("Executing single watch scan...")
            from src.channel_watcher import ChannelWatcher
            w = ChannelWatcher(cookies_file=args.cookies, cookies_from_browser=args.cookies_from_browser, browser=args.browser)
            processed = w.execute_scan(upload=args.upload)
            logger.info(f"Scan complete. Processed {processed} videos.")
            sys.exit(0)
            
        elif args.watch_daemon:
            logger.info("Starting watcher daemon (pressing Ctrl+C to stop)...")
            from src.channel_watcher import ChannelWatcher
            import time
            w = ChannelWatcher(cookies_file=args.cookies, cookies_from_browser=args.cookies_from_browser, browser=args.browser)
            interval = 3600
            if args.watch_time:
                try:
                    interval = int(args.watch_time)
                except ValueError:
                    logger.warning("Could not parse watch_time as int seconds, using 3600s.")
            try:
                while True:
                    w.execute_scan(upload=args.upload)
                    logger.info(f"Sleeping for {interval}s")
                    time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("Daemon stopped.")
            sys.exit(0)

        elif args.daily_summary:
            from src.daily_summary import generate_daily_summary
            date_str = None if args.daily_summary == 'today' else args.daily_summary
            url = generate_daily_summary(target_date=date_str, upload=args.upload)
            print(f"Daily summary generated: {url}")
            sys.exit(0)

        elif args.batch:
            # Batch file mode
            batch_file = Path(args.batch)
            if not batch_file.exists():
                log_error(f"Batch file does not exist: {batch_file}")
                sys.exit(1)

            logger.info("Batch processing mode")
            logger.info(f"Batch file: {batch_file.absolute()}")

            results = _process_batch_file(
                batch_file,
                cookies_file=args.cookies,
                cookies_from_browser=args.cookies_from_browser,
                browser=args.browser,
                keep_audio=args.keep_audio,
                summary_style=args.style,
                upload=args.upload
            )

        elif args.local:
            # Local MP3 folder mode
            folder_path = Path(args.local)
            if not folder_path.exists():
                log_error(f"Folder does not exist: {folder_path}")
                sys.exit(1)
            if not folder_path.is_dir():
                log_error(f"Path is not a folder: {folder_path}")
                sys.exit(1)

            logger.info("Local MP3 folder mode")
            logger.info(f"Folder path: {folder_path.absolute()}")

            results = process_local_folder(
                folder_path,
                summary_style=args.style,
                upload_to_github_repo=args.upload
            )

        elif args.apple_podcast_single:
            # Apple Podcasts single episode mode
            logger.info("Apple Podcasts single episode mode")
            result = process_apple_podcast(
                args.apple_podcast_single,
                episode_index=0,  # Latest episode
                summary_style=args.style,
                upload_to_github_repo=args.upload
            )

        elif args.apple_podcast_list:
            # Apple Podcasts show (all episodes) mode
            logger.info("Apple Podcasts show mode")
            results = process_apple_podcast_show(
                args.apple_podcast_list,
                summary_style=args.style,
                upload_to_github_repo=args.upload
            )

        elif args.list:
            # YouTube playlist mode
            logger.info("YouTube playlist mode")
            results = process_playlist(
                args.list,
                cookies_file=args.cookies,
                cookies_from_browser=args.cookies_from_browser,
                browser=args.browser,
                keep_audio=args.keep_audio,
                summary_style=args.style,
                upload_to_github_repo=args.upload
            )

        elif args.video:
            # YouTube single video mode
            logger.info("YouTube single video mode")
            result = process_video(
                args.video,
                cookies_file=args.cookies,
                cookies_from_browser=args.cookies_from_browser,
                browser=args.browser,
                keep_audio=args.keep_audio,
                summary_style=args.style,
                upload_to_github_repo=args.upload
            )

        elif args.url:
            # Default mode (backward compatible) - auto-detect URL type
            if is_apple_podcasts_url(args.url):
                logger.info("Detected Apple Podcasts URL (single episode)")
                result = process_apple_podcast(
                    args.url,
                    episode_index=0,
                    summary_style=args.style,
                    upload_to_github_repo=args.upload
                )
            elif is_playlist_url(args.url):
                logger.info("Detected YouTube playlist")
                results = process_playlist(
                    args.url,
                    cookies_file=args.cookies,
                    cookies_from_browser=args.cookies_from_browser,
                    browser=args.browser,
                    keep_audio=args.keep_audio,
                    summary_style=args.style,
                    upload_to_github_repo=args.upload
                )
            else:
                logger.info("Detected YouTube single video")
                result = process_video(
                    args.url,
                    cookies_file=args.cookies,
                    cookies_from_browser=args.cookies_from_browser,
                    browser=args.browser,
                    keep_audio=args.keep_audio,
                    summary_style=args.style,
                    upload_to_github_repo=args.upload
                )

        else:
            # No input provided
            log_error("Please provide input parameters")
            logger.info("Usage:")
            logger.info("  python src/main.py -video <YouTube video URL>")
            logger.info("  python src/main.py -list <YouTube playlist URL>")
            logger.info("  python src/main.py --apple-podcast-single <Apple Podcasts URL>")
            logger.info("  python src/main.py --apple-podcast-list <Apple Podcasts URL>")
            logger.info("  python src/main.py -local <MP3 folder path>")
            logger.info("  python src/main.py --batch <input file>")
            logger.info("Or use default mode:")
            logger.info("  python src/main.py <URL>")
            logger.info("Use --help for detailed help")
            sys.exit(1)

        # Generate daily summary if upload is configured
        if args.upload and (config.GITHUB_TOKEN and config.GITHUB_REPO):
            try:
                from src.daily_summary import generate_daily_summary
                logger.info("")
                logger.info("="*60)
                log_step("Final", "Generating and uploading daily digest...")
                generate_daily_summary(upload=True)
            except Exception as e:
                logger.warning(f"Failed to generate daily digest: {e}")

        # Upload logs and database to GitHub if configured
        if args.upload and (config.GITHUB_TOKEN and config.GITHUB_REPO):
            logger.info("")
            logger.info("="*60)
            log_step("Final", "Uploading logs and database to GitHub...")
            try:
                # Get current log file path
                current_log = get_current_log_file()
                log_results = upload_logs_to_github(current_log)
                if log_results['db_url']:
                    logger.info(f"  Database: {log_results['db_url']}")
                if log_results['log_files']:
                    logger.info(f"  Uploaded {len(log_results['log_files'])} log file(s)")
                logger.info("Logs uploaded successfully!")
            except Exception as e:
                logger.warning(f"Failed to upload logs: {e}")

        sys.exit(0)

    except KeyboardInterrupt:
        log_error("User interrupted")
        sys.exit(1)
    except Exception as e:
        log_error(f"Program exited abnormally: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
