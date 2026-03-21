"""CLI参数解析模块

提供统一的命令行参数解析接口。
"""

import argparse
from typing import Optional


def create_parser() -> argparse.ArgumentParser:
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
    watcher_group.add_argument('--import-watchlist', type=str, metavar='FILE',
                               help='Import channel URLs from text file into watchlist')
    watcher_group.add_argument('--list-watch-channels', action='store_true',
                               help='List currently monitored channels')
    watcher_group.add_argument('--watch-run-once', action='store_true',
                               help='Execute a single watch scan across all active channels')
    watcher_group.add_argument('--watch-daemon', action='store_true',
                               help='Run the watcher continuously (daemon mode)')
    watcher_group.add_argument('--watch-time', type=str,
                               help='Interval for daemon execution (seconds)')

    summary_group = parser.add_argument_group('summary')
    summary_group.add_argument('--daily-summary', type=str, nargs='?', const='today',
                               metavar='DATE', help='Generate daily summary (optional format: YYYYMMDD)')

    return parser
