import yt_dlp
from pathlib import Path
from typing import Dict, Optional, List
import logging

from config import config
from .utils import sanitize_filename, extract_video_id, find_ffmpeg_location, extract_playlist_id

logger = logging.getLogger(__name__)


class YouTubeHandler:
    """Handle YouTube video download and metadata extraction"""

    def __init__(self, cookies_file: Optional[str] = None):
        """
        Initialize YouTube handler

        Args:
            cookies_file: Path to cookies.txt file (for membership videos)
        """
        self.cookies_file = cookies_file
        self.temp_dir = config.TEMP_DIR

    def get_video_info(self, url: str) -> Dict:
        """
        Get video information (without downloading)

        Args:
            url: YouTube video URL

        Returns:
            Dictionary containing video information
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }

        if self.cookies_file:
            ydl_opts['cookiefile'] = self.cookies_file

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                return {
                    'id': info.get('id'),
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'description': info.get('description'),
                    'uploader': info.get('uploader'),
                    'upload_date': info.get('upload_date'),
                    'view_count': info.get('view_count'),
                    'has_subtitles': bool(info.get('subtitles') or info.get('automatic_captions'))
                }
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            raise

    def download_audio(self, url: str, video_id: Optional[str] = None) -> Path:
        """
        Download video audio

        Args:
            url: YouTube video URL
            video_id: Video ID (optional, used for file naming)

        Returns:
            Path to downloaded audio file
        """
        if video_id is None:
            video_id = extract_video_id(url)
            if video_id is None:
                raise ValueError("Could not extract video ID from URL")

        output_file = self.temp_dir / f"{video_id}.{config.AUDIO_FORMAT}"

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': config.AUDIO_FORMAT,
                'preferredquality': config.AUDIO_QUALITY,
            }],
            'outtmpl': str(self.temp_dir / f"{video_id}.%(ext)s"),
            'quiet': False,
            'no_warnings': False,
        }

        # Add FFmpeg location (if found)
        ffmpeg_location = find_ffmpeg_location()
        if ffmpeg_location:
            ydl_opts['ffmpeg_location'] = ffmpeg_location

        if self.cookies_file:
            ydl_opts['cookiefile'] = self.cookies_file

        try:
            logger.info(f"Downloading audio for video: {video_id}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            logger.info(f"Audio downloaded: {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"Failed to download audio: {e}")
            raise

    def download_subtitles(self, url: str, video_id: Optional[str] = None,
                          lang: str = 'zh') -> Optional[Path]:
        """
        Download video subtitles (if available)

        Args:
            url: YouTube video URL
            video_id: Video ID
            lang: Subtitle language code

        Returns:
            Path to subtitle file, or None if unavailable
        """
        if video_id is None:
            video_id = extract_video_id(url)

        output_path = config.TRANSCRIPT_DIR / f"{video_id}"

        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': [lang, 'en'],  # Try multiple languages
            'subtitlesformat': 'srt',
            'outtmpl': str(output_path),
            'quiet': True,
        }

        if self.cookies_file:
            ydl_opts['cookiefile'] = self.cookies_file

        try:
            logger.info(f"Attempting to download subtitles for: {video_id}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Find downloaded subtitle files
            subtitle_files = list(config.TRANSCRIPT_DIR.glob(f"{video_id}*.srt"))
            if subtitle_files:
                logger.info(f"Subtitles downloaded: {subtitle_files[0]}")
                return subtitle_files[0]
            else:
                logger.info("No subtitles available")
                return None

        except Exception as e:
            logger.warning(f"Failed to download subtitles: {e}")
            return None


def get_playlist_videos(playlist_url: str, cookies_file: Optional[str] = None) -> List[str]:
    """
    Get all video URLs from a playlist

    Args:
        playlist_url: YouTube playlist URL
        cookies_file: Path to cookies.txt file

    Returns:
        List of video URLs
    """
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True,
    }

    if cookies_file:
        ydl_opts['cookiefile'] = cookies_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(playlist_url, download=False)

            if 'entries' not in result:
                logger.error("No entries found in playlist")
                return []

            video_urls = []
            for entry in result['entries']:
                if entry and 'id' in entry:
                    video_id = entry['id']
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    video_urls.append(video_url)

            logger.info(f"Found {len(video_urls)} videos in playlist")
            return video_urls

    except Exception as e:
        logger.error(f"Failed to get playlist videos: {e}")
        raise


def process_youtube_video(url: str, cookies_file: Optional[str] = None) -> Dict:
    """
    Process YouTube video (convenience function)

    Args:
        url: YouTube video URL
        cookies_file: Path to cookies.txt file

    Returns:
        Dictionary containing video information and file paths
    """
    handler = YouTubeHandler(cookies_file)

    # Get video information
    info = handler.get_video_info(url)
    video_id = info['id']

    # Try to download subtitles
    subtitle_path = handler.download_subtitles(url, video_id)

    # If no subtitles, download audio for transcription
    audio_path = None
    if subtitle_path is None:
        audio_path = handler.download_audio(url, video_id)

    return {
        'info': info,
        'video_id': video_id,
        'subtitle_path': subtitle_path,
        'audio_path': audio_path,
        'needs_transcription': subtitle_path is None
    }
