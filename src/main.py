#!/usr/bin/env python3
"""YouTube视频转录和摘要工具 - 主入口点

业务逻辑函数保留在本模块中，CLI逻辑委托给src.cli模块。
"""

import sys
from pathlib import Path
from typing import Optional, List

# Ensure project root is on sys.path so imports work whether the user runs
# `python src/main.py` or `python -m src.main` from the repository root.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from colorama import init

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
from src.cli import create_parser, CommandHandler, display_banner

init(autoreset=True)
logger = setup_logging()


def process_video(
    url: str,
    cookies_file: Optional[str] = None,
    cookies_from_browser: bool = True,
    browser: str = "chrome",
    keep_audio: bool = False,
    summary_style: str = "detailed",
    upload_to_github_repo: bool = False
) -> dict:
    pipeline = ProcessingPipeline(
        run_type='youtube',
        url_or_path=url,
        identifier='',
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
) -> List[dict]:
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
) -> List[dict]:
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
    logger.info("[1/3] Fetching podcast episode information...")
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
) -> List[dict]:
    return process_podcast_show_batch(
        url, summary_style=summary_style, upload=upload_to_github_repo
    )


def process_batch_file(
    batch_file: Path,
    cookies_file: Optional[str] = None,
    cookies_from_browser: bool = True,
    browser: str = "chrome",
    keep_audio: bool = False,
    summary_style: str = "detailed",
    upload_to_github_repo: bool = False
) -> dict:
    return _process_batch_file(
        batch_file,
        cookies_file=cookies_file,
        cookies_from_browser=cookies_from_browser,
        browser=browser,
        keep_audio=keep_audio,
        summary_style=summary_style,
        upload=upload_to_github_repo
    )


def process_resume_only(summary_style: str = "detailed", upload: bool = False) -> dict:
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


def main():
    display_banner()
    parser = create_parser()
    args = parser.parse_args()
    handler = CommandHandler(args)
    handler.execute()


if __name__ == '__main__':
    main()
