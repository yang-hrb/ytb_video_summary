"""Batch processing module (Phase 2.7).

Contains logic for processing playlists, podcast shows, local folders, and
mixed batch files.  All functions share a single Transcriber instance so
the Whisper model is only loaded once per process.
"""

import logging
from pathlib import Path
from typing import Optional, List

from src.pipeline import ProcessingPipeline
from src.transcriber import Transcriber
from src.github_handler import upload_to_github

logger = logging.getLogger(__name__)


def _make_shared_transcriber() -> Transcriber:
    """Pre-load the Whisper model once for an entire batch session."""
    t = Transcriber()
    t.load_model()
    return t


# ---------------------------------------------------------------------------
# YouTube playlist
# ---------------------------------------------------------------------------

def process_playlist_batch(
    playlist_url: str,
    cookies_file: Optional[str] = None,
    cookies_from_browser: bool = False,
    browser: str = "chrome",
    keep_audio: bool = False,
    summary_style: str = "detailed",
    upload: bool = False,
) -> list:
    """Process all videos in a YouTube playlist.

    Returns a list of result dicts (one per video).  Failed videos are
    included with an 'error' key.
    """
    from src.youtube_handler import get_playlist_videos
    from src.utils import extract_playlist_id

    playlist_id = extract_playlist_id(playlist_url)
    logger.info("Fetching playlist %s …", playlist_id)
    video_urls = get_playlist_videos(
        playlist_url,
        cookies_file=cookies_file,
        cookies_from_browser=cookies_from_browser,
        browser=browser,
    )

    if not video_urls:
        logger.error("No videos found in playlist")
        return []

    logger.info("Found %d video(s) in playlist", len(video_urls))
    shared_transcriber = _make_shared_transcriber()
    results = []
    failed: List[tuple] = []

    for idx, url in enumerate(video_urls, 1):
        logger.info("=" * 60)
        logger.info("Playlist video [%d/%d]", idx, len(video_urls))
        logger.info("=" * 60)
        try:
            pipeline = ProcessingPipeline(
                run_type='youtube',
                url_or_path=url,
                identifier='',  # will be filled after download
                summary_style=summary_style,
                upload=upload,
                transcriber=shared_transcriber,
            )
            result = pipeline.run_youtube(
                cookies_file=cookies_file,
                cookies_from_browser=cookies_from_browser,
                browser=browser,
                keep_audio=keep_audio,
            )
            results.append(result)
        except Exception as e:
            logger.error("Video [%d] failed: %s", idx, e)
            logger.debug("Details", exc_info=True)
            failed.append((idx, url, str(e)))
            results.append({'error': str(e), 'url': url})

    _log_summary("Playlist", len(video_urls), len(results) - len(failed), len(failed), failed)
    return results


# ---------------------------------------------------------------------------
# Podcast show (all episodes)
# ---------------------------------------------------------------------------

def process_podcast_show_batch(
    url: str,
    summary_style: str = "detailed",
    upload: bool = False,
) -> list:
    """Process all episodes from an Apple Podcasts show."""
    from src.apple_podcasts_handler import get_podcast_episodes, process_apple_podcast_episode

    logger.info("Fetching podcast show …")
    episodes = get_podcast_episodes(url)

    if not episodes:
        logger.error("No episodes found")
        return []

    podcast_info = episodes[0].get('podcast_info', {})
    logger.info("Podcast: %s | %d episode(s)", podcast_info.get('title', '?'), len(episodes))

    shared_transcriber = _make_shared_transcriber()
    results = []
    failed: List[tuple] = []

    for idx, ep_info in enumerate(episodes):
        logger.info("=" * 60)
        logger.info("Episode [%d/%d]: %s", idx + 1, len(episodes), ep_info.get('title', ''))
        logger.info("=" * 60)
        try:
            dl_result = process_apple_podcast_episode(url, idx)
            audio_path = dl_result['audio_path']
            identifier = dl_result['identifier']
            video_info = {
                'title': ep_info.get('title', identifier),
                'uploader': podcast_info.get('artist', podcast_info.get('title', 'Unknown')),
                'duration': ep_info.get('duration', 0),
            }
            pipeline = ProcessingPipeline(
                run_type='podcast',
                url_or_path=url,
                identifier=identifier,
                summary_style=summary_style,
                upload=upload,
                transcriber=shared_transcriber,
            )
            result = pipeline.run_podcast(audio_path, video_info)
            result.update({'podcast_info': podcast_info, 'episode_info': ep_info})
            results.append(result)
        except Exception as e:
            logger.error("Episode [%d] failed: %s", idx + 1, e)
            logger.debug("Details", exc_info=True)
            failed.append((idx + 1, ep_info.get('title', ''), str(e)))
            results.append({'error': str(e), 'episode': ep_info})

    _log_summary("Podcast show", len(episodes), len(results) - len(failed), len(failed), failed)
    return results


# ---------------------------------------------------------------------------
# Local folder (all MP3 files)
# ---------------------------------------------------------------------------

def process_local_folder_batch(
    folder_path: Path,
    summary_style: str = "detailed",
    upload: bool = False,
) -> list:
    """Process every MP3 in a folder."""
    mp3_files = list(folder_path.glob("*.mp3"))
    if not mp3_files:
        logger.error("No MP3 files found in: %s", folder_path)
        return []

    logger.info("Found %d MP3 file(s) in %s", len(mp3_files), folder_path)
    shared_transcriber = _make_shared_transcriber()
    results = []
    failed: List[tuple] = []

    for idx, mp3_file in enumerate(mp3_files, 1):
        logger.info("=" * 60)
        logger.info("MP3 file [%d/%d]: %s", idx, len(mp3_files), mp3_file.name)
        logger.info("=" * 60)
        try:
            pipeline = ProcessingPipeline(
                run_type='local',
                url_or_path=str(mp3_file),
                identifier=mp3_file.stem,
                summary_style=summary_style,
                upload=upload,
                transcriber=shared_transcriber,
            )
            result = pipeline.run_local_mp3(mp3_file)
            if upload and result.get('report_file'):
                try:
                    github_url = upload_to_github(result['report_file'])
                    result['github_url'] = github_url
                    if github_url:
                        logger.info("GitHub URL: %s", github_url)
                except Exception as e:
                    logger.warning("GitHub upload failed for %s: %s", mp3_file.name, e)
                    result['github_url'] = None
            results.append(result)
        except Exception as e:
            logger.error("MP3 [%d] failed: %s", idx, e)
            logger.debug("Details", exc_info=True)
            failed.append((idx, mp3_file.name, str(e)))
            results.append({'error': str(e), 'file': str(mp3_file)})

    _log_summary("Local folder", len(mp3_files), len(results) - len(failed), len(failed), failed)
    return results


# ---------------------------------------------------------------------------
# Mixed batch file
# ---------------------------------------------------------------------------

def process_batch_file(
    batch_file: Path,
    cookies_file: Optional[str] = None,
    cookies_from_browser: bool = False,
    browser: str = "chrome",
    keep_audio: bool = False,
    summary_style: str = "detailed",
    upload: bool = False,
) -> dict:
    """Process a mixed batch file (YouTube URLs, playlist URLs, local paths)."""
    from src.utils import is_playlist_url, is_apple_podcasts_url

    if not batch_file.exists():
        logger.error("Batch file not found: %s", batch_file)
        return {'success': False, 'error': 'File not found'}

    with open(batch_file, 'r', encoding='utf-8') as f:
        raw_lines = f.readlines()

    inputs = [
        (i, ln.strip())
        for i, ln in enumerate(raw_lines, 1)
        if ln.strip() and not ln.strip().startswith('#')
    ]

    if not inputs:
        logger.error("No valid inputs in batch file")
        return {'success': False, 'error': 'No valid inputs'}

    logger.info("Found %d input(s) in batch file", len(inputs))
    shared_transcriber = _make_shared_transcriber()

    stats = {'total': len(inputs), 'processed': 0, 'failed': 0, 'items': []}

    for idx, (line_num, line) in enumerate(inputs, 1):
        logger.info("=" * 60)
        logger.info("Batch input [%d/%d] (line %d): %s", idx, len(inputs), line_num, line)
        logger.info("=" * 60)

        item = {'line_number': line_num, 'input': line, 'success': False, 'error': None}
        try:
            if line.startswith('http://') or line.startswith('https://'):
                if is_apple_podcasts_url(line):
                    from src.apple_podcasts_handler import process_apple_podcast_episode
                    dl = process_apple_podcast_episode(line, 0)
                    video_info = {
                        'title': dl.get('episode_info', {}).get('title', dl['identifier']),
                        'uploader': dl.get('podcast_info', {}).get('title', 'Unknown'),
                        'duration': dl.get('episode_info', {}).get('duration', 0),
                    }
                    pipeline = ProcessingPipeline(
                        run_type='podcast', url_or_path=line,
                        identifier=dl['identifier'], summary_style=summary_style,
                        upload=upload, transcriber=shared_transcriber,
                    )
                    item['result'] = pipeline.run_podcast(dl['audio_path'], video_info)
                elif is_playlist_url(line):
                    item['result'] = process_playlist_batch(
                        line, cookies_file=cookies_file,
                        cookies_from_browser=cookies_from_browser, browser=browser,
                        keep_audio=keep_audio, summary_style=summary_style, upload=upload,
                    )
                else:
                    pipeline = ProcessingPipeline(
                        run_type='youtube', url_or_path=line,
                        identifier='', summary_style=summary_style,
                        upload=upload, transcriber=shared_transcriber,
                    )
                    item['result'] = pipeline.run_youtube(
                        cookies_file=cookies_file,
                        cookies_from_browser=cookies_from_browser,
                        browser=browser, keep_audio=keep_audio,
                    )
            else:
                folder = Path(line)
                if folder.exists() and folder.is_dir():
                    item['result'] = process_local_folder_batch(
                        folder, summary_style=summary_style, upload=upload,
                    )
                else:
                    raise ValueError(f"Unknown input: {line}")

            item['success'] = True
            stats['processed'] += 1
        except Exception as e:
            logger.error("Failed: %s", e)
            logger.debug("Details", exc_info=True)
            item['error'] = str(e)
            stats['failed'] += 1

        stats['items'].append(item)

    _log_summary("Batch", stats['total'], stats['processed'], stats['failed'],
                 [(i['line_number'], i['input'], i['error'])
                  for i in stats['items'] if not i['success']])
    stats['success'] = True
    return stats


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _log_summary(label: str, total: int, success: int, failed: int, failed_items):
    logger.info("=" * 60)
    logger.info("%s processing complete", label)
    logger.info("=" * 60)
    logger.info("Total: %d | Success: %d | Failed: %d", total, success, failed)
    if failed_items:
        logger.warning("Failed items:")
        for item in failed_items:
            if len(item) == 3:
                logger.warning("  [%s] %s — %s", item[0], item[1], item[2])
