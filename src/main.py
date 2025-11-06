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
from src.utils import clean_temp_files, get_file_size_mb, is_playlist_url, extract_playlist_id, sanitize_filename, is_apple_podcasts_url
from src.github_handler import upload_to_github, upload_logs_to_github
from src.run_tracker import get_tracker, log_failure

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
    keep_audio: bool = False,
    summary_style: str = "detailed",
    upload_to_github_repo: bool = False
) -> dict:
    """
    Process a single video through the complete pipeline

    Args:
        url: YouTube video URL
        cookies_file: Path to cookies.txt file
        keep_audio: Whether to keep downloaded audio file
        summary_style: Summary style (brief/detailed)
        upload_to_github_repo: Whether to upload report to GitHub

    Returns:
        Dictionary containing processing results
    """
    # Initialize run tracking
    tracker = get_tracker()
    run_id = None
    video_id = None

    try:
        # Step 1: Download video info and subtitles/audio
        log_step("1/4", "Fetching video information...")
        result = process_youtube_video(url, cookies_file)

        video_info = result['info']
        video_id = result['video_id']

        # Start tracking this run
        run_id = tracker.start_run('youtube', url, video_id)
        tracker.update_status(run_id, 'working')

        logger.info(f"  Title: {video_info['title']}")
        logger.info(f"  Duration: {video_info['duration']}s")
        logger.info(f"  Uploader: {video_info['uploader']}")

        # Step 2: Get transcript text and detect language
        transcript = None
        detected_language = config.SUMMARY_LANGUAGE  # Use configured summary language

        if result['needs_transcription']:
            log_step("2/4", "Transcribing audio with Whisper...")
            audio_path = result['audio_path']
            logger.info(f"  Audio file: {audio_path}")
            logger.info(f"  File size: {get_file_size_mb(audio_path):.2f} MB")

            transcript, whisper_language = transcribe_video_audio(audio_path, video_id, save_srt=True)

            # Clean up audio file
            if not keep_audio and not config.KEEP_AUDIO:
                logger.info("  Cleaning up audio file...")
                audio_path.unlink()
        else:
            log_step("2/4", "Reading subtitle file...")
            subtitle_path = result['subtitle_path']
            logger.info(f"  Subtitle file: {subtitle_path}")
            transcript, whisper_language = read_subtitle_file(subtitle_path)

        logger.info(f"  Transcript length: {len(transcript)} characters")
        logger.info(f"  Detected language: {whisper_language}")

        # Step 3: Generate AI summary
        log_step("3/4", "Generating AI summary...")
        logger.info(f"  Using style: {summary_style}")
        logger.info(f"  Summary language: {detected_language}")

        summary_result = summarize_transcript(
            transcript,
            video_id,
            video_info,
            style=summary_style,
            language=detected_language,
            video_url=url
        )

        # Step 4: Output results
        log_step("4/4", "Processing complete!")

        transcript_file = config.TRANSCRIPT_DIR / f"{video_id}_transcript.srt"
        summary_file = summary_result['summary_path']
        report_file = summary_result['report_path']
        github_url = None

        logger.info("Output files:")
        logger.info(f"  Transcript: {transcript_file}")
        logger.info(f"  Summary: {summary_file}")
        if report_file:
            logger.info(f"  Report: {report_file}")

        # Upload to GitHub if requested
        if upload_to_github_repo and report_file:
            log_step("Bonus", "Uploading report to GitHub...")
            try:
                github_url = upload_to_github(report_file)
                if github_url:
                    logger.info(f"GitHub URL: {github_url}")
            except Exception as e:
                logger.warning(f"GitHub upload failed: {e}")

        log_success("Video processing complete!")

        # Mark run as done
        if run_id:
            tracker.update_status(run_id, 'done')

        return {
            'video_id': video_id,
            'video_info': video_info,
            'transcript': transcript,
            'transcript_file': transcript_file,
            'summary_file': summary_file,
            'report_file': report_file,
            'github_url': github_url
        }

    except Exception as e:
        log_error(f"Processing failed: {e}")
        logger.exception("Error processing video")

        # Mark run as failed and log to failure file
        if run_id:
            tracker.update_status(run_id, 'failed', str(e))
        if video_id:
            log_failure('youtube', video_id, url, str(e))

        raise


def process_local_mp3(
    mp3_path: Path,
    summary_style: str = "detailed",
    upload_to_github_repo: bool = False
) -> dict:
    """
    Process a local MP3 file through the complete pipeline

    Args:
        mp3_path: Path to MP3 file
        summary_style: Summary style (brief/detailed)
        upload_to_github_repo: Whether to upload report to GitHub

    Returns:
        Dictionary containing processing results
    """
    # Initialize run tracking
    tracker = get_tracker()
    run_id = None
    file_name = None

    try:
        file_name = mp3_path.stem  # Filename without extension

        # Start tracking this run
        run_id = tracker.start_run('local', str(mp3_path), mp3_path.name)
        tracker.update_status(run_id, 'working')

        logger.info(f"  File: {mp3_path.name}")
        logger.info(f"  Size: {get_file_size_mb(mp3_path):.2f} MB")

        # Step 1: Transcribe audio
        log_step("1/3", "Transcribing audio with Whisper...")

        transcriber = Transcriber()
        result = transcriber.transcribe_audio(mp3_path)
        transcript = transcriber.get_transcript_text(result)

        # Detect language from transcription (for reference only)
        whisper_language = result.get('language', 'en')

        # Save SRT file
        srt_path = config.TRANSCRIPT_DIR / f"{file_name}_transcript.srt"
        transcriber.save_as_srt(result, srt_path)

        logger.info(f"  Transcript length: {len(transcript)} characters")
        logger.info(f"  Detected language: {whisper_language}")

        # Step 2: Generate AI summary
        log_step("2/3", "Generating AI summary...")
        summary_language = config.SUMMARY_LANGUAGE  # Use configured summary language
        logger.info(f"  Using style: {summary_style}")
        logger.info(f"  Summary language: {summary_language}")

        # Create virtual video_info for local files
        video_info = {
            'title': file_name,
            'uploader': 'Local Audio',
            'duration': int(result.get('segments', [{}])[-1].get('end', 0)) if result.get('segments') else 0
        }

        summary_result = summarize_transcript(
            transcript,
            file_name,
            video_info,
            style=summary_style,
            language=summary_language,
            video_url=None
        )

        # Step 3: Output results
        log_step("3/3", "Processing complete!")

        summary_file = summary_result['summary_path']
        report_file = summary_result['report_path']
        github_url = None

        logger.info("Output files:")
        logger.info(f"  Transcript: {srt_path}")
        logger.info(f"  Summary: {summary_file}")
        if report_file:
            logger.info(f"  Report: {report_file}")

        # Upload to GitHub if requested
        if upload_to_github_repo and report_file:
            log_step("Bonus", "Uploading report to GitHub...")
            try:
                github_url = upload_to_github(report_file)
                if github_url:
                    logger.info(f"GitHub URL: {github_url}")
            except Exception as e:
                logger.warning(f"GitHub upload failed: {e}")

        log_success("Audio processing complete!")

        # Mark run as done
        if run_id:
            tracker.update_status(run_id, 'done')

        return {
            'file_name': file_name,
            'file_path': mp3_path,
            'transcript': transcript,
            'transcript_file': srt_path,
            'summary_file': summary_file,
            'report_file': report_file,
            'github_url': github_url
        }

    except Exception as e:
        log_error(f"Processing failed: {e}")
        logger.exception("Error processing local MP3")

        # Mark run as failed and log to failure file
        if run_id:
            tracker.update_status(run_id, 'failed', str(e))
        if file_name:
            log_failure('local', mp3_path.name, str(mp3_path), str(e))

        raise


def process_local_folder(
    folder_path: Path,
    summary_style: str = "detailed",
    upload_to_github_repo: bool = False
) -> list:
    """
    Process all MP3 files in a local folder

    Args:
        folder_path: Path to folder
        summary_style: Summary style (brief/detailed)
        upload_to_github_repo: Whether to upload reports to GitHub after each file

    Returns:
        List containing all file processing results
    """
    try:
        # Find all MP3 files
        log_step("0", "Scanning for MP3 files...")
        mp3_files = list(folder_path.glob("*.mp3"))

        if not mp3_files:
            log_error(f"No MP3 files found in folder: {folder_path}")
            return []

        logger.info(f"  Found {len(mp3_files)} MP3 files")
        logger.info("Starting MP3 file processing...")

        # Process each file
        results = []
        failed_files = []

        for idx, mp3_file in enumerate(mp3_files, 1):
            logger.info("="*60)
            logger.info(f"Processing file [{idx}/{len(mp3_files)}]")
            logger.info("="*60)

            try:
                # Process the MP3 file
                result = process_local_mp3(
                    mp3_file,
                    summary_style=summary_style,
                    upload_to_github_repo=False  # We'll handle upload here for each iteration
                )

                # Upload to GitHub immediately after processing (if requested)
                if upload_to_github_repo and result.get('report_file'):
                    try:
                        logger.info("Uploading report to GitHub for this file...")
                        github_url = upload_to_github(result['report_file'])
                        result['github_url'] = github_url
                        if github_url:
                            logger.info(f"GitHub URL: {github_url}")
                    except Exception as e:
                        logger.warning(f"GitHub upload failed for file {idx}: {e}")
                        result['github_url'] = None

                results.append(result)
            except Exception as e:
                log_error(f"File {idx} processing failed: {e}")
                logger.exception(f"Failed to process file {idx}: {mp3_file}")
                failed_files.append((idx, mp3_file.name, str(e)))
                # Continue processing next file
                continue

        # Output summary
        logger.info("="*60)
        logger.info("Folder processing complete")
        logger.info("="*60)

        logger.info(f"Successfully processed: {len(results)}/{len(mp3_files)} files")

        if failed_files:
            logger.warning("Failed files:")
            for idx, filename, error in failed_files:
                logger.warning(f"  [{idx}] {filename}")
                logger.warning(f"      Error: {error}")

        return results

    except Exception as e:
        log_error(f"Folder processing failed: {e}")
        logger.exception("Error processing local folder")
        raise


def process_playlist(
    playlist_url: str,
    cookies_file: Optional[str] = None,
    keep_audio: bool = False,
    summary_style: str = "detailed",
    upload_to_github_repo: bool = False
) -> list:
    """
    Process all videos in a playlist

    Args:
        playlist_url: YouTube playlist URL
        cookies_file: Path to cookies.txt file
        keep_audio: Whether to keep downloaded audio files
        summary_style: Summary style (brief/detailed)
        upload_to_github_repo: Whether to upload reports to GitHub after each video

    Returns:
        List containing all video processing results
    """
    try:
        # Get all videos from playlist
        log_step("0", "Fetching playlist information...")
        playlist_id = extract_playlist_id(playlist_url)
        logger.info(f"  Playlist ID: {playlist_id}")

        video_urls = get_playlist_videos(playlist_url, cookies_file)

        if not video_urls:
            log_error("No videos found in playlist")
            return []

        logger.info(f"  Found {len(video_urls)} videos")
        logger.info("Starting playlist video processing...")

        # Process each video
        results = []
        failed_videos = []

        for idx, video_url in enumerate(video_urls, 1):
            logger.info("="*60)
            logger.info(f"Processing video [{idx}/{len(video_urls)}]")
            logger.info("="*60)

            try:
                # Process the video
                result = process_video(
                    video_url,
                    cookies_file=cookies_file,
                    keep_audio=keep_audio,
                    summary_style=summary_style,
                    upload_to_github_repo=False  # We'll handle upload here for each iteration
                )

                # Upload to GitHub immediately after processing (if requested)
                if upload_to_github_repo and result.get('report_file'):
                    try:
                        logger.info("Uploading report to GitHub for this video...")
                        github_url = upload_to_github(result['report_file'])
                        result['github_url'] = github_url
                        if github_url:
                            logger.info(f"GitHub URL: {github_url}")
                    except Exception as e:
                        logger.warning(f"GitHub upload failed for video {idx}: {e}")
                        result['github_url'] = None

                results.append(result)
            except Exception as e:
                log_error(f"Video {idx} processing failed: {e}")
                logger.exception(f"Failed to process video {idx}: {video_url}")
                failed_videos.append((idx, video_url, str(e)))
                # Continue processing next video
                continue

        # Output summary
        logger.info("="*60)
        logger.info("Playlist processing complete")
        logger.info("="*60)

        logger.info(f"Successfully processed: {len(results)}/{len(video_urls)} videos")

        if failed_videos:
            logger.warning("Failed videos:")
            for idx, url, error in failed_videos:
                logger.warning(f"  [{idx}] {url}")
                logger.warning(f"      Error: {error}")

        return results

    except Exception as e:
        log_error(f"Playlist processing failed: {e}")
        logger.exception("Error processing playlist")
        raise


def process_apple_podcast(
    url: str,
    episode_index: int = 0,
    summary_style: str = "detailed",
    upload_to_github_repo: bool = False
) -> dict:
    """
    Process a single Apple Podcasts episode through the complete pipeline

    Args:
        url: Apple Podcasts URL
        episode_index: Episode index (0 = latest)
        summary_style: Summary style (brief/detailed)
        upload_to_github_repo: Whether to upload report to GitHub

    Returns:
        Dictionary containing processing results
    """
    # Initialize run tracking
    tracker = get_tracker()
    run_id = None
    identifier = None

    try:
        # Step 1: Download podcast episode audio
        log_step("1/3", "Fetching podcast episode information...")
        result = process_apple_podcast_episode(url, episode_index)

        podcast_info = result['podcast_info']
        episode_info = result['episode_info']
        audio_path = result['audio_path']
        identifier = result['identifier']

        # Start tracking this run
        run_id = tracker.start_run('podcast', url, identifier)
        tracker.update_status(run_id, 'working')

        logger.info(f"  Podcast: {podcast_info['title']}")
        logger.info(f"  Episode: {episode_info['title']}")
        if episode_info.get('duration'):
            logger.info(f"  Duration: {episode_info['duration']}s")

        # Step 2: Transcribe audio
        log_step("2/3", "Transcribing audio with Whisper...")
        logger.info(f"  Audio file: {audio_path}")
        logger.info(f"  File size: {get_file_size_mb(audio_path):.2f} MB")

        transcriber = Transcriber()
        transcribe_result = transcriber.transcribe_audio(audio_path)
        transcript = transcriber.get_transcript_text(transcribe_result)

        # Detect language from transcription
        whisper_language = transcribe_result.get('language', 'en')

        # Save SRT file
        srt_path = config.TRANSCRIPT_DIR / f"{identifier}_transcript.srt"
        transcriber.save_as_srt(transcribe_result, srt_path)

        # Clean up audio file
        if not config.KEEP_AUDIO:
            logger.info("  Cleaning up audio file...")
            audio_path.unlink()

        logger.info(f"  Transcript length: {len(transcript)} characters")
        logger.info(f"  Detected language: {whisper_language}")

        # Step 3: Generate AI summary
        log_step("3/3", "Generating AI summary...")
        summary_language = config.SUMMARY_LANGUAGE
        logger.info(f"  Using style: {summary_style}")
        logger.info(f"  Summary language: {summary_language}")

        # Create virtual video_info for podcast episodes
        video_info = {
            'title': episode_info['title'],
            'uploader': podcast_info.get('artist', podcast_info.get('title', 'Unknown Podcast')),
            'duration': episode_info.get('duration', 0)
        }

        summary_result = summarize_transcript(
            transcript,
            identifier,
            video_info,
            style=summary_style,
            language=summary_language,
            video_url=url
        )

        # Output results
        log_step("Done", "Processing complete!")

        summary_file = summary_result['summary_path']
        report_file = summary_result['report_path']
        github_url = None

        logger.info("Output files:")
        logger.info(f"  Transcript: {srt_path}")
        logger.info(f"  Summary: {summary_file}")
        if report_file:
            logger.info(f"  Report: {report_file}")

        # Upload to GitHub if requested
        if upload_to_github_repo and report_file:
            log_step("Bonus", "Uploading report to GitHub...")
            try:
                github_url = upload_to_github(report_file)
                if github_url:
                    logger.info(f"GitHub URL: {github_url}")
            except Exception as e:
                logger.warning(f"GitHub upload failed: {e}")

        log_success("Podcast episode processing complete!")

        # Mark run as done
        if run_id:
            tracker.update_status(run_id, 'done')

        return {
            'identifier': identifier,
            'podcast_info': podcast_info,
            'episode_info': episode_info,
            'transcript': transcript,
            'transcript_file': srt_path,
            'summary_file': summary_file,
            'report_file': report_file,
            'github_url': github_url
        }

    except Exception as e:
        log_error(f"Processing failed: {e}")
        logger.exception("Error processing podcast episode")

        # Mark run as failed and log to failure file
        if run_id:
            tracker.update_status(run_id, 'failed', str(e))
        if identifier:
            log_failure('podcast', identifier, url, str(e))

        raise


def process_apple_podcast_show(
    url: str,
    summary_style: str = "detailed",
    upload_to_github_repo: bool = False
) -> list:
    """
    Process all episodes from an Apple Podcasts show

    Args:
        url: Apple Podcasts show URL
        summary_style: Summary style (brief/detailed)
        upload_to_github_repo: Whether to upload reports to GitHub after each episode

    Returns:
        List containing all episode processing results
    """
    try:
        # Get all episodes from show
        log_step("0", "Fetching podcast show information...")

        episodes = get_podcast_episodes(url)

        if not episodes:
            log_error("No episodes found in podcast show")
            return []

        podcast_info = episodes[0]['podcast_info']
        logger.info(f"  Podcast: {podcast_info['title']}")
        logger.info(f"  Found {len(episodes)} episodes")
        logger.info("Starting podcast show processing...")

        # Process each episode
        results = []
        failed_episodes = []

        for idx, episode_info in enumerate(episodes):
            logger.info("="*60)
            logger.info(f"Processing episode [{idx+1}/{len(episodes)}]")
            logger.info(f"  Title: {episode_info['title']}")
            logger.info("="*60)

            try:
                # Process the episode (episode_index is same as current index)
                result = process_apple_podcast(
                    url,
                    episode_index=idx,
                    summary_style=summary_style,
                    upload_to_github_repo=False  # We'll handle upload here
                )

                # Upload to GitHub immediately after processing (if requested)
                if upload_to_github_repo and result.get('report_file'):
                    try:
                        logger.info("Uploading report to GitHub for this episode...")
                        github_url = upload_to_github(result['report_file'])
                        result['github_url'] = github_url
                        if github_url:
                            logger.info(f"GitHub URL: {github_url}")
                    except Exception as e:
                        logger.warning(f"GitHub upload failed for episode {idx+1}: {e}")
                        result['github_url'] = None

                results.append(result)
            except Exception as e:
                log_error(f"Episode {idx+1} processing failed: {e}")
                logger.exception(f"Failed to process episode {idx+1}: {episode_info['title']}")
                failed_episodes.append((idx+1, episode_info['title'], str(e)))
                # Continue processing next episode
                continue

        # Output summary
        logger.info("="*60)
        logger.info("Podcast show processing complete")
        logger.info("="*60)

        logger.info(f"Successfully processed: {len(results)}/{len(episodes)} episodes")

        if failed_episodes:
            logger.warning("Failed episodes:")
            for idx, title, error in failed_episodes:
                logger.warning(f"  [{idx}] {title}")
                logger.warning(f"      Error: {error}")

        return results

    except Exception as e:
        log_error(f"Podcast show processing failed: {e}")
        logger.exception("Error processing podcast show")
        raise


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
                logger.exception(f"Error processing line {line_num}")
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
        logger.exception("Error in batch processing")
        return {'success': False, 'error': str(e)}


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

    # Keep positional argument for backward compatibility
    parser.add_argument(
        'url',
        nargs='?',
        help='YouTube video or playlist URL (default mode)'
    )

    parser.add_argument(
        '--cookies',
        type=str,
        help='Path to cookies.txt file (for membership videos)'
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
        '--upload',
        action='store_true',
        help='Upload report files to GitHub repository'
    )

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
        if args.batch:
            # Batch file mode
            batch_file = Path(args.batch)
            if not batch_file.exists():
                log_error(f"Batch file does not exist: {batch_file}")
                sys.exit(1)

            logger.info("Batch processing mode")
            logger.info(f"Batch file: {batch_file.absolute()}")

            results = process_batch_file(
                batch_file,
                cookies_file=args.cookies,
                keep_audio=args.keep_audio,
                summary_style=args.style,
                upload_to_github_repo=args.upload
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
                    keep_audio=args.keep_audio,
                    summary_style=args.style,
                    upload_to_github_repo=args.upload
                )
            else:
                logger.info("Detected YouTube single video")
                result = process_video(
                    args.url,
                    cookies_file=args.cookies,
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
