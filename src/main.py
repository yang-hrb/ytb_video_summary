#!/usr/bin/env python3
"""
Audio/Video Transcription & Summarization Tool - Main Program
"""

import argparse
import sys
from pathlib import Path
import logging
from typing import Optional

from colorama import init, Fore, Style

# Ensure project root is on sys.path so imports work whether the user runs
# `python src/main.py` or `python -m src.main` from the repository root.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import config
from src.youtube_handler import process_youtube_video, get_playlist_videos
from src.transcriber import transcribe_video_audio, read_subtitle_file, Transcriber
from src.summarizer import summarize_transcript
from src.utils import clean_temp_files, get_file_size_mb, is_playlist_url, extract_playlist_id, sanitize_filename
from src.github_handler import upload_to_github

# Initialize colorama
init(autoreset=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('youtube_summarizer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print program banner"""
    banner = f"""
{Fore.CYAN}╔═══════════════════════════════════════════════════════════╗
║   Audio/Video Transcript & Summarizer v2.0                ║
║   Supports: YouTube Videos/Playlists + Local MP3          ║
╚═══════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)


def print_step(step: str, description: str):
    """Print step information"""
    print(f"\n{Fore.GREEN}[{step}]{Style.RESET_ALL} {description}")


def print_error(message: str):
    """Print error message"""
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {message}")


def print_success(message: str):
    """Print success message"""
    print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {message}")


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
        print_step("1/4", "Fetching video information...")
        result = process_youtube_video(url, cookies_file)

        video_info = result['info']
        video_id = result['video_id']

        print(f"  Title: {video_info['title']}")
        print(f"  Duration: {video_info['duration']}s")
        print(f"  Uploader: {video_info['uploader']}")

        # Step 2: Get transcript text and detect language
        transcript = None
        detected_language = 'en'

        if result['needs_transcription']:
            print_step("2/4", "Transcribing audio with Whisper...")
            audio_path = result['audio_path']
            print(f"  Audio file: {audio_path}")
            print(f"  File size: {get_file_size_mb(audio_path):.2f} MB")

            transcript, detected_language = transcribe_video_audio(audio_path, video_id, save_srt=True)

            # Clean up audio file
            if not keep_audio and not config.KEEP_AUDIO:
                print("  Cleaning up audio file...")
                audio_path.unlink()
        else:
            print_step("2/4", "Reading subtitle file...")
            subtitle_path = result['subtitle_path']
            print(f"  Subtitle file: {subtitle_path}")
            transcript, detected_language = read_subtitle_file(subtitle_path)

        print(f"  Transcript length: {len(transcript)} characters")
        print(f"  Detected language: {detected_language}")

        # Step 3: Generate AI summary
        print_step("3/4", "Generating AI summary...")
        print(f"  Using style: {summary_style}")
        print(f"  Summary language: {detected_language}")

        summary_result = summarize_transcript(
            transcript,
            video_id,
            video_info,
            style=summary_style,
            language=detected_language,
            video_url=url
        )

        # Step 4: Output results
        print_step("4/4", "Processing complete!")

        transcript_file = config.TRANSCRIPT_DIR / f"{video_id}_transcript.srt"
        summary_file = summary_result['summary_path']
        report_file = summary_result['report_path']
        github_url = None

        print(f"\n{Fore.CYAN}Output files:{Style.RESET_ALL}")
        print(f"  Transcript: {transcript_file}")
        print(f"  Summary: {summary_file}")
        if report_file:
            print(f"  Report: {report_file}")

        # Upload to GitHub if requested
        if upload_to_github_repo and report_file:
            print_step("Bonus", "Uploading report to GitHub...")
            try:
                github_url = upload_to_github(report_file)
                if github_url:
                    print(f"\n{Fore.CYAN}GitHub:{Style.RESET_ALL}")
                    print(f"  {github_url}")
            except Exception as e:
                logger.error(f"GitHub upload failed: {e}")
                print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} GitHub upload failed: {e}")

        print_success("Video processing complete!")

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
        print_error(f"Processing failed: {e}")
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

        print(f"  File: {mp3_path.name}")
        print(f"  Size: {get_file_size_mb(mp3_path):.2f} MB")

        # Step 1: Transcribe audio
        print_step("1/3", "Transcribing audio with Whisper...")

        transcriber = Transcriber()
        result = transcriber.transcribe_audio(mp3_path)
        transcript = transcriber.get_transcript_text(result)

        # Detect language from transcription
        detected_language = result.get('language', 'en')

        # Save SRT file
        srt_path = config.TRANSCRIPT_DIR / f"{file_name}_transcript.srt"
        transcriber.save_as_srt(result, srt_path)

        print(f"  Transcript length: {len(transcript)} characters")
        print(f"  Detected language: {detected_language}")

        # Step 2: Generate AI summary
        print_step("2/3", "Generating AI summary...")
        print(f"  Using style: {summary_style}")
        print(f"  Summary language: {detected_language}")

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
            language=detected_language,
            video_url=None
        )

        # Step 3: Output results
        print_step("3/3", "Processing complete!")

        summary_file = summary_result['summary_path']
        report_file = summary_result['report_path']
        github_url = None

        print(f"\n{Fore.CYAN}Output files:{Style.RESET_ALL}")
        print(f"  Transcript: {srt_path}")
        print(f"  Summary: {summary_file}")
        if report_file:
            print(f"  Report: {report_file}")

        # Upload to GitHub if requested
        if upload_to_github_repo and report_file:
            print_step("Bonus", "Uploading report to GitHub...")
            try:
                github_url = upload_to_github(report_file)
                if github_url:
                    print(f"\n{Fore.CYAN}GitHub:{Style.RESET_ALL}")
                    print(f"  {github_url}")
            except Exception as e:
                logger.error(f"GitHub upload failed: {e}")
                print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} GitHub upload failed: {e}")

        print_success("Audio processing complete!")

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
        print_error(f"Processing failed: {e}")
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

    Returns:
        List containing all file processing results
    """
    try:
        # Find all MP3 files
        print_step("0", "Scanning for MP3 files...")
        mp3_files = list(folder_path.glob("*.mp3"))

        if not mp3_files:
            print_error(f"No MP3 files found in folder: {folder_path}")
            return []

        print(f"  Found {len(mp3_files)} MP3 files")
        print(f"\n{Fore.YELLOW}Starting MP3 file processing...{Style.RESET_ALL}\n")

        # Process each file
        results = []
        failed_files = []

        for idx, mp3_file in enumerate(mp3_files, 1):
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Processing file [{idx}/{len(mp3_files)}]{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

            try:
                result = process_local_mp3(
                    mp3_file,
                    summary_style=summary_style,
                    upload_to_github_repo=upload_to_github_repo
                )
                results.append(result)
            except Exception as e:
                print_error(f"File {idx} processing failed: {e}")
                logger.exception(f"Failed to process file {idx}: {mp3_file}")
                failed_files.append((idx, mp3_file.name, str(e)))
                # Continue processing next file
                continue

        # Output summary
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Folder processing complete{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        print(f"{Fore.GREEN}Successfully processed: {len(results)}/{len(mp3_files)} files{Style.RESET_ALL}")

        if failed_files:
            print(f"\n{Fore.YELLOW}Failed files:{Style.RESET_ALL}")
            for idx, filename, error in failed_files:
                print(f"  [{idx}] {filename}")
                print(f"      Error: {error}")

        return results

    except Exception as e:
        print_error(f"Folder processing failed: {e}")
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

    Returns:
        List containing all video processing results
    """
    try:
        # Get all videos from playlist
        print_step("0", "Fetching playlist information...")
        playlist_id = extract_playlist_id(playlist_url)
        print(f"  Playlist ID: {playlist_id}")

        video_urls = get_playlist_videos(playlist_url, cookies_file)

        if not video_urls:
            print_error("No videos found in playlist")
            return []

        print(f"  Found {len(video_urls)} videos")
        print(f"\n{Fore.YELLOW}Starting playlist video processing...{Style.RESET_ALL}\n")

        # Process each video
        results = []
        failed_videos = []

        for idx, video_url in enumerate(video_urls, 1):
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Processing video [{idx}/{len(video_urls)}]{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

            try:
                result = process_video(
                    video_url,
                    cookies_file=cookies_file,
                    keep_audio=keep_audio,
                    summary_style=summary_style,
                    upload_to_github_repo=upload_to_github_repo
                )
                results.append(result)
            except Exception as e:
                print_error(f"Video {idx} processing failed: {e}")
                logger.exception(f"Failed to process video {idx}: {video_url}")
                failed_videos.append((idx, video_url, str(e)))
                # Continue processing next video
                continue

        # Output summary
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Playlist processing complete{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        print(f"{Fore.GREEN}Successfully processed: {len(results)}/{len(video_urls)} videos{Style.RESET_ALL}")

        if failed_videos:
            print(f"\n{Fore.YELLOW}Failed videos:{Style.RESET_ALL}")
            for idx, url, error in failed_videos:
                print(f"  [{idx}] {url}")
                print(f"      Error: {error}")

        return results

    except Exception as e:
        print_error(f"Playlist processing failed: {e}")
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
        print_error(str(e))
        print("\nPlease ensure OPENROUTER_API_KEY is set in .env file")
        sys.exit(1)

    # Determine processing mode
    try:
        if args.local:
            # Local MP3 folder mode
            folder_path = Path(args.local)
            if not folder_path.exists():
                print_error(f"Folder does not exist: {folder_path}")
                sys.exit(1)
            if not folder_path.is_dir():
                print_error(f"Path is not a folder: {folder_path}")
                sys.exit(1)

            print(f"{Fore.YELLOW}Local MP3 folder mode{Style.RESET_ALL}\n")
            print(f"Folder path: {folder_path.absolute()}\n")

            results = process_local_folder(
                folder_path,
                summary_style=args.style,
                upload_to_github_repo=args.upload
            )

        elif args.list:
            # YouTube playlist mode
            print(f"{Fore.YELLOW}YouTube playlist mode{Style.RESET_ALL}\n")
            results = process_playlist(
                args.list,
                cookies_file=args.cookies,
                keep_audio=args.keep_audio,
                summary_style=args.style,
                upload_to_github_repo=args.upload
            )

        elif args.video:
            # YouTube single video mode
            print(f"{Fore.YELLOW}YouTube single video mode{Style.RESET_ALL}\n")
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
                print(f"{Fore.YELLOW}Detected YouTube playlist{Style.RESET_ALL}\n")
                results = process_playlist(
                    args.url,
                    cookies_file=args.cookies,
                    keep_audio=args.keep_audio,
                    summary_style=args.style,
                    upload_to_github_repo=args.upload
                )
            else:
                print(f"{Fore.YELLOW}Detected YouTube single video{Style.RESET_ALL}\n")
                result = process_video(
                    args.url,
                    cookies_file=args.cookies,
                    keep_audio=args.keep_audio,
                    summary_style=args.style,
                    upload_to_github_repo=args.upload
                )

        else:
            # No input provided
            print_error("Please provide input parameters")
            print("\nUsage:")
            print("  python src/main.py -video <YouTube video URL>")
            print("  python src/main.py -list <YouTube playlist URL>")
            print("  python src/main.py -local <MP3 folder path>")
            print("\nOr use default mode:")
            print("  python src/main.py <YouTube URL>")
            print("\nUse --help for detailed help")
            sys.exit(1)

        sys.exit(0)

    except KeyboardInterrupt:
        print_error("\nUser interrupted")
        sys.exit(1)
    except Exception as e:
        print_error(f"Program exited abnormally: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
