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
from src.logger import setup_logging, get_logger
from src.youtube_handler import process_youtube_video, get_playlist_videos
from src.transcriber import transcribe_video_audio, read_subtitle_file, Transcriber
from src.summarizer import summarize_transcript
from src.utils import clean_temp_files, get_file_size_mb, is_playlist_url, extract_playlist_id, sanitize_filename
from src.github_handler import upload_to_github

# Initialize colorama
init(autoreset=True)

# Initialize logging system
logger = setup_logging()


def print_banner():
    """Print program banner"""
    banner = f"""
{Fore.CYAN}╔═══════════════════════════════════════════════════════════╗
║   Audio/Video Transcript & Summarizer v2.0                ║
║   Supports: YouTube Videos/Playlists + Local MP3          ║
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
    try:
        # Step 1: Download video info and subtitles/audio
        log_step("1/4", "Fetching video information...")
        result = process_youtube_video(url, cookies_file)

        video_info = result['info']
        video_id = result['video_id']

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
    try:
        file_name = mp3_path.stem  # Filename without extension

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


def main():
    """Main function - CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Audio/Video Transcription & Summarization Tool - Supports YouTube and Local MP3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single YouTube video (default)
  python src/main.py "https://youtube.com/watch?v=xxxxx"
  python src/main.py -video "https://youtube.com/watch?v=xxxxx" --style brief

  # Process YouTube playlist
  python src/main.py -list "https://youtube.com/playlist?list=xxxxx"
  python src/main.py -list "https://youtube.com/watch?v=xxxxx&list=xxxxx"

  # Process local MP3 folder
  python src/main.py -local /path/to/mp3/folder
  python src/main.py -local ./audio_files --style detailed
        """
    )

    # Create mutually exclusive group: -video, -list, -local (choose one)
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
        '-local',
        type=str,
        metavar='PATH',
        help='Local MP3 folder path'
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
        if args.local:
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
            # Default mode (backward compatible) - auto-detect YouTube URL type
            if is_playlist_url(args.url):
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
            logger.info("  python src/main.py -local <MP3 folder path>")
            logger.info("Or use default mode:")
            logger.info("  python src/main.py <YouTube URL>")
            logger.info("Use --help for detailed help")
            sys.exit(1)

        sys.exit(0)

    except KeyboardInterrupt:
        log_error("User interrupted")
        sys.exit(1)
    except Exception as e:
        log_error(f"Program exited abnormally: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
