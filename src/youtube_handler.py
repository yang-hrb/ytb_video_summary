import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional, TypeVar

import yt_dlp
from yt_dlp.utils import DownloadError

try:
    from yt_dlp.cookies import CookieLoadError
except ImportError:  # pragma: no cover - fallback for older yt-dlp versions
    try:
        from yt_dlp.utils import CookieLoadError
    except ImportError:  # pragma: no cover - last-resort fallback
        class CookieLoadError(Exception):
            pass

from config import config
from .utils import extract_video_id, find_ffmpeg_location

logger = logging.getLogger(__name__)
T = TypeVar("T")

CHROME_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _retry_sleep_http(retry_count: int) -> int:
    return min(5 * retry_count, 60)


def build_ydl_opts(
    *,
    cookies_file: Optional[str],
    cookies_from_browser: bool,
    browser: str,
    overrides: Optional[Dict] = None,
) -> Dict:
    ydl_opts: Dict = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": False,
        "user_agent": CHROME_USER_AGENT,
        "referer": "https://www.youtube.com/",
        "sleep_interval": 3,
        "max_sleep_interval": 6,
        "concurrent_fragment_downloads": 1,
        "retries": 10,
        "fragment_retries": 10,
        "extractor_retries": 10,
        "retry_sleep_functions": {"http": _retry_sleep_http},
    }

    cookies_path = Path(cookies_file) if cookies_file else None
    if cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (browser,)
    elif cookies_path and cookies_path.exists():
        ydl_opts["cookiefile"] = str(cookies_path)
    elif cookies_path and not cookies_path.exists():
        logger.warning("cookies.txt file not found: %s", cookies_path)

    if overrides:
        ydl_opts.update(overrides)

    return ydl_opts


def _log_download_error(
    error: Exception,
    *,
    cookies_from_browser: bool,
    cookies_file: Optional[str],
) -> None:
    message = str(error)
    lower_message = message.lower()

    if "http error 403" in lower_message or "forbidden" in lower_message:
        logger.error(
            "403 Forbidden: likely YouTube session not trusted. "
            "Open Chrome, sign in to YouTube, then retry."
        )
        if not cookies_from_browser:
            logger.error(
                "Try --cookies-from-browser to use your local Chrome session."
            )
        if cookies_file:
            logger.error(
                "cookies.txt is often invalid across machines; "
                "prefer --cookies-from-browser."
            )
        return

    if "http error 429" in lower_message or "too many requests" in lower_message:
        logger.error(
            "YouTube rate limit detected (HTTP 429). "
            "Please wait and retry."
        )
        return

    if any(
        phrase in lower_message
        for phrase in ("timed out", "timeout", "temporary", "connection", "network")
    ):
        logger.error(
            "Temporary network issue detected. Please retry after a short wait."
        )
        return

    if "sign in" in lower_message or "login" in lower_message:
        logger.error(
            "YouTube requires a valid login. "
            "Sign in with Chrome and retry with --cookies-from-browser."
        )
        return

    logger.error("YouTube download failed: %s", message)


def _execute_ydl(
    *,
    ydl_opts: Dict,
    action: Callable[[yt_dlp.YoutubeDL], T],
    context: str,
    cookies_from_browser: bool,
    cookies_file: Optional[str],
) -> T:
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return action(ydl)
    except DownloadError as exc:
        _log_download_error(
            exc,
            cookies_from_browser=cookies_from_browser,
            cookies_file=cookies_file,
        )
        logger.debug("Download error details:", exc_info=True)
        raise
    except Exception as exc:
        logger.error("%s failed: %s", context, exc)
        logger.debug("Detailed error information:", exc_info=True)
        raise


def _run_ydl_with_cookie_fallback(
    *,
    cookies_file: Optional[str],
    cookies_from_browser: bool,
    browser: str,
    ydl_opts: Dict,
    action: Callable[[yt_dlp.YoutubeDL], T],
    context: str,
) -> T:
    try:
        return _execute_ydl(
            ydl_opts=ydl_opts,
            action=action,
            context=context,
            cookies_from_browser=cookies_from_browser,
            cookies_file=cookies_file,
        )
    except CookieLoadError:
        if cookies_from_browser and cookies_file:
            logger.warning(
                "Could not read %s cookies. Falling back to cookies.txt.",
                browser,
            )
            fallback_opts = dict(ydl_opts)
            fallback_opts.pop("cookiesfrombrowser", None)
            cookies_path = Path(cookies_file)
            if cookies_path.exists():
                fallback_opts["cookiefile"] = str(cookies_path)
            else:
                fallback_opts.pop("cookiefile", None)
                logger.warning("cookies.txt file not found: %s", cookies_path)
            return _execute_ydl(
                ydl_opts=fallback_opts,
                action=action,
                context=context,
                cookies_from_browser=False,
                cookies_file=cookies_file,
            )

        logger.error(
            "Could not read %s cookies (is the browser installed and accessible?).",
            browser,
        )
        logger.debug("Cookie load error details:", exc_info=True)
        raise


class YouTubeHandler:
    """Handle YouTube video download and metadata extraction"""

    def __init__(
        self,
        cookies_file: Optional[str] = None,
        cookies_from_browser: bool = False,
        browser: str = "chrome",
    ):
        """
        Initialize YouTube handler

        Args:
            cookies_file: Path to cookies.txt file (for membership videos)
            cookies_from_browser: Read cookies from local browser profile (default: disabled)
            browser: Browser name for cookiesfrombrowser (default: chrome)
        """
        self.cookies_file = cookies_file
        self.cookies_from_browser = cookies_from_browser
        self.browser = browser
        self.temp_dir = config.TEMP_DIR
        self._log_cookie_strategy()

    def _log_cookie_strategy(self) -> None:
        if self.cookies_from_browser:
            logger.info(
                "Using browser cookies from %s (override with --no-cookies-from-browser).",
                self.browser,
            )
        elif self.cookies_file:
            logger.info("Using cookies.txt file: %s", self.cookies_file)
        else:
            logger.warning(
                "No cookies configured. YouTube may require login and return 403."
            )

    def get_video_info(self, url: str) -> Dict:
        """
        Get video information (without downloading)

        Args:
            url: YouTube video URL

        Returns:
            Dictionary containing video information
        """
        ydl_opts = build_ydl_opts(
            cookies_file=self.cookies_file,
            cookies_from_browser=self.cookies_from_browser,
            browser=self.browser,
            overrides={
                "extract_flat": False,
            },
        )

        try:
            info = _run_ydl_with_cookie_fallback(
                cookies_file=self.cookies_file,
                cookies_from_browser=self.cookies_from_browser,
                browser=self.browser,
                ydl_opts=ydl_opts,
                context="Fetching video info",
                action=lambda ydl: ydl.extract_info(url, download=False),
            )

            return {
                "id": info.get("id"),
                "title": info.get("title"),
                "duration": info.get("duration"),
                "description": info.get("description"),
                "uploader": info.get("uploader"),
                "upload_date": info.get("upload_date"),
                "view_count": info.get("view_count"),
                "has_subtitles": bool(info.get("subtitles") or info.get("automatic_captions")),
            }
        except Exception as e:
            logger.error("Failed to get video info: %s", e)
            logger.debug("Detailed error information:", exc_info=True)
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

        ydl_opts = build_ydl_opts(
            cookies_file=self.cookies_file,
            cookies_from_browser=self.cookies_from_browser,
            browser=self.browser,
            overrides={
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": config.AUDIO_FORMAT,
                        "preferredquality": config.AUDIO_QUALITY,
                    }
                ],
                "outtmpl": str(self.temp_dir / f"{video_id}.%(ext)s"),
            },
        )

        # Add FFmpeg location (if found)
        ffmpeg_location = find_ffmpeg_location()
        if ffmpeg_location:
            ydl_opts['ffmpeg_location'] = ffmpeg_location

        try:
            logger.info("Downloading audio for video: %s", video_id)
            _run_ydl_with_cookie_fallback(
                cookies_file=self.cookies_file,
                cookies_from_browser=self.cookies_from_browser,
                browser=self.browser,
                ydl_opts=ydl_opts,
                context="Downloading audio",
                action=lambda ydl: ydl.download([url]),
            )

            logger.info("Audio downloaded: %s", output_file)
            return output_file

        except Exception as e:
            logger.error("Failed to download audio: %s", e)
            logger.debug("Detailed error information:", exc_info=True)
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

        ydl_opts = build_ydl_opts(
            cookies_file=self.cookies_file,
            cookies_from_browser=self.cookies_from_browser,
            browser=self.browser,
            overrides={
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": [lang, "en"],  # Try multiple languages
                "subtitlesformat": "srt",
                "outtmpl": str(output_path),
            },
        )

        try:
            logger.info("Attempting to download subtitles for: %s", video_id)
            _run_ydl_with_cookie_fallback(
                cookies_file=self.cookies_file,
                cookies_from_browser=self.cookies_from_browser,
                browser=self.browser,
                ydl_opts=ydl_opts,
                context="Downloading subtitles",
                action=lambda ydl: ydl.download([url]),
            )

            # Find downloaded subtitle files
            subtitle_files = list(config.TRANSCRIPT_DIR.glob(f"{video_id}*.srt"))
            if subtitle_files:
                logger.info("Subtitles downloaded: %s", subtitle_files[0])
                return subtitle_files[0]
            else:
                logger.info("No subtitles available")
                return None

        except Exception as e:
            logger.warning("Failed to download subtitles: %s", e)
            logger.debug("Detailed error information:", exc_info=True)
            return None


def get_playlist_videos(
    playlist_url: str,
    cookies_file: Optional[str] = None,
    cookies_from_browser: bool = False,
    browser: str = "chrome",
) -> List[str]:
    """
    Get all video URLs from a playlist

    Args:
        playlist_url: YouTube playlist URL
        cookies_file: Path to cookies.txt file
        cookies_from_browser: Read cookies from local browser profile (default: disabled)
        browser: Browser name for cookiesfrombrowser (default: chrome)

    Returns:
        List of video URLs
    """
    if not cookies_from_browser and not cookies_file:
        logger.warning(
            "No cookies configured for playlist. YouTube may return 403."
        )

    ydl_opts = build_ydl_opts(
        cookies_file=cookies_file,
        cookies_from_browser=cookies_from_browser,
        browser=browser,
        overrides={
            "extract_flat": True,
        },
    )

    try:
        result = _run_ydl_with_cookie_fallback(
            cookies_file=cookies_file,
            cookies_from_browser=cookies_from_browser,
            browser=browser,
            ydl_opts=ydl_opts,
            context="Fetching playlist videos",
            action=lambda ydl: ydl.extract_info(playlist_url, download=False),
        )

        if "entries" not in result:
            logger.error("No entries found in playlist")
            return []

        video_urls = []
        for entry in result["entries"]:
            if entry and "id" in entry:
                video_id = entry["id"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                video_urls.append(video_url)

        logger.info("Found %s videos in playlist", len(video_urls))
        return video_urls

    except Exception as e:
        logger.error("Failed to get playlist videos: %s", e)
        logger.debug("Detailed error information:", exc_info=True)
        raise


def process_youtube_video(
    url: str,
    cookies_file: Optional[str] = None,
    cookies_from_browser: bool = False,
    browser: str = "chrome",
) -> Dict:
    """
    Process YouTube video (convenience function)

    Args:
        url: YouTube video URL
        cookies_file: Path to cookies.txt file
        cookies_from_browser: Read cookies from local browser profile (default: disabled)
        browser: Browser name for cookiesfrombrowser (default: chrome)

    Returns:
        Dictionary containing video information and file paths
    """
    handler = YouTubeHandler(
        cookies_file=cookies_file,
        cookies_from_browser=cookies_from_browser,
        browser=browser,
    )

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
