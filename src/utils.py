import os
import re
import logging
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize filename by removing illegal characters

    Args:
        filename: Original filename
        max_length: Maximum length

    Returns:
        Sanitized filename
    """
    # Keep only Chinese characters, English letters, digits, and spaces
    filename = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', '', filename)
    # Replace one or more spaces with a single underscore, and strip ends
    filename = re.sub(r'\s+', '_', filename).strip('_')
    # Limit length
    if len(filename) > max_length:
        filename = filename[:max_length]
    return filename


def get_category_folder(channel_name: str) -> str:
    """
    Determine the category folder for a channel based on the first character of its name.

    Mapping:
      0-9          → 00_number
      A-Z (a-z)   → NN_X_letter  (e.g. A→01_A_letter, B→02_B_letter … Z→26_Z_letter)
      Chinese/CJK → resolved via pinyin initial letter then same mapping above

    Args:
        channel_name: The raw channel / uploader name

    Returns:
        Category folder string, e.g. ``"13_M_letter"``
    """
    if not channel_name:
        return "00_number"

    first_char = channel_name[0]

    if first_char.isdigit():
        return "00_number"

    upper_char = first_char.upper()

    if upper_char.isalpha() and ord('A') <= ord(upper_char) <= ord('Z'):
        num = ord(upper_char) - ord('A') + 1
        return f"{num:02d}_{upper_char}_letter"

    # Chinese / CJK characters: derive pinyin initial via pypinyin if available,
    # otherwise fall back to a hardcoded common-character table.
    try:
        from pypinyin import lazy_pinyin, Style
        pinyin_list = lazy_pinyin(first_char, style=Style.FIRST_LETTER)
        if pinyin_list and pinyin_list[0]:
            initial = pinyin_list[0][0].upper()
            if 'A' <= initial <= 'Z':
                num = ord(initial) - ord('A') + 1
                return f"{num:02d}_{initial}_letter"
    except ImportError:
        pass

    # Minimal fallback table for the most common CJK initials used in channel names
    _CJK_INITIALS: dict[str, str] = {
        # 七 qī
        '\u4e03': 'Q',
        # 向 xiàng
        '\u5411': 'X',
        # 立 lì
        '\u7acb': 'L',
        # 中 zhōng
        '\u4e2d': 'Z',
        # 大 dà
        '\u5927': 'D',
        # 新 xīn
        '\u65b0': 'X',
        # 美 měi
        '\u7f8e': 'M',
        # 华 huá
        '\u534e': 'H',
        # 人 rén
        '\u4eba': 'R',
        # 台 tái
        '\u53f0': 'T',
        # 政 zhèng
        '\u653f': 'Z',
        # 当 dāng
        '\u5f53': 'D',
    }
    initial = _CJK_INITIALS.get(first_char)
    if initial:
        num = ord(initial) - ord('A') + 1
        return f"{num:02d}_{initial}_letter"

    # Last resort: treat as number bucket
    logger.warning("Cannot determine category folder for channel starting with %r; using 00_number", first_char)
    return "00_number"


def extract_summary_title(summary: str, max_length: int = 50) -> str:
    """
    Extract title from summary content

    Args:
        summary: AI-generated summary content
        max_length: Maximum title length

    Returns:
        Extracted title
    """
    # Try to extract title from summary section
    lines = summary.split('\n')
    for line in lines:
        line = line.strip()
        # Skip heading markers and empty lines
        if line and not line.startswith('#') and not line.startswith('**') and len(line) > 10:
            # Remove possible list markers
            title = line.lstrip('-•*> ').strip()
            if title:
                # Limit length and sanitize
                title = sanitize_filename(title, max_length=max_length)
                return title

    # Return default if extraction fails
    return "summary"


def create_report_filename(video_title: str, uploader: str = "", upload_date: str = "", summary: str = "", is_local_mp3: bool = False) -> str:
    """
    Create report filename

    For local MP3: timestamp_mp3_filename.md
    For videos: timestamp_uploader_content-title.md

    Args:
        video_title: Video title (or MP3 filename without extension)
        uploader: Uploader name (first 10 characters)
        upload_date: The video's upload date (YYYYMMDD) or similar timestamp
        summary: Summary content (for generating content-related title)
        is_local_mp3: True if processing local MP3 file

    Returns:
        Formatted filename
    """
    timestamp = upload_date or datetime.now().strftime("%Y%m%d")

    # Special format for local MP3 files: timestamp_mp3_filename.md
    if is_local_mp3:
        clean_filename = sanitize_filename(video_title, max_length=100)
        return f"{datetime.now().strftime('%Y%m%d_%H%M')}_mp3_{clean_filename}.md"

    # Standard format for videos: timestamp_uploader_content-title.md
    uploader_part = ""
    if uploader:
        clean_uploader = sanitize_filename(uploader, max_length=15)
        if clean_uploader:
            uploader_part = f"{clean_uploader}_"

    content_title = sanitize_filename(video_title, max_length=20)

    return f"{timestamp}_{uploader_part}{content_title}.md"


def format_duration(seconds: int) -> str:
    """
    Convert seconds to readable duration format

    Args:
        seconds: Number of seconds

    Returns:
        Formatted duration (HH:MM:SS or MM:SS)
    """
    # Use total_seconds() to correctly handle durations > 24 hours
    # (timedelta.seconds wraps around at 86400, causing incorrect results for long streams)
    total = int(timedelta(seconds=seconds).total_seconds())
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def format_timestamp(seconds: float) -> str:
    """
    Convert seconds to SRT timestamp format

    Args:
        seconds: Number of seconds

    Returns:
        SRT format timestamp (HH:MM:SS,mmm)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


# clean_temp_files() removed — audio cleanup is done inline via audio_path.unlink()
# ensure_dir_exists() removed — directory creation is handled centrally by Config.__init__()


def get_file_size_mb(file_path: Path) -> float:
    """
    Get file size in MB

    Args:
        file_path: File path

    Returns:
        File size in MB
    """
    if not file_path.exists():
        return 0.0
    return file_path.stat().st_size / (1024 * 1024)


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract video ID from YouTube URL

    Args:
        url: YouTube URL

    Returns:
        Video ID or None
    """
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)',
        r'youtube\.com\/embed\/([^&\n?#]+)',
        r'youtube\.com\/v\/([^&\n?#]+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def is_playlist_url(url: str) -> bool:
    """
    Detect if URL is a YouTube playlist

    Args:
        url: YouTube URL

    Returns:
        True if playlist URL, False otherwise
    """
    playlist_patterns = [
        r'youtube\.com\/playlist\?list=',
        r'youtube\.com\/watch\?.*list=',
    ]

    for pattern in playlist_patterns:
        if re.search(pattern, url):
            return True

    return False


def extract_playlist_id(url: str) -> Optional[str]:
    """
    Extract playlist ID from YouTube URL

    Args:
        url: YouTube URL

    Returns:
        Playlist ID or None
    """
    pattern = r'[?&]list=([^&\n?#]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)

    return None


def create_summary_header(title: str, duration: str, timestamp: Optional[str] = None) -> str:
    """
    Create summary file header

    Args:
        title: Video title
        duration: Video duration
        timestamp: Generation timestamp

    Returns:
        Markdown formatted header
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    header = f"""# {title}

**Duration**: {duration}
**Generated**: {timestamp}

---

"""
    return header





def find_ffmpeg_location() -> Optional[str]:
    """
    Find FFmpeg executable location

    Returns:
        FFmpeg directory path, or None if not found
    """
    # 1. Check environment variable
    ffmpeg_env = os.getenv('FFMPEG_LOCATION')
    if ffmpeg_env and Path(ffmpeg_env).exists():
        logger.info(f"Using FFmpeg from environment variable: {ffmpeg_env}")
        return ffmpeg_env

    # 2. Check ffmpeg in PATH
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        ffmpeg_dir = str(Path(ffmpeg_path).parent)
        logger.info(f"Found FFmpeg in PATH: {ffmpeg_dir}")
        return ffmpeg_dir

    # 3. Check common installation locations
    common_locations = [
        '/opt/homebrew/bin',  # macOS Homebrew (Apple Silicon)
        '/usr/local/bin',     # macOS Homebrew (Intel) / Linux
        '/usr/bin',           # Linux
        'C:\\ffmpeg\\bin',    # Windows
        'C:\\Program Files\\ffmpeg\\bin',  # Windows
    ]

    for location in common_locations:
        ffmpeg_file = Path(location) / 'ffmpeg'
        if ffmpeg_file.exists() or Path(f"{ffmpeg_file}.exe").exists():
            logger.info(f"Found FFmpeg at: {location}")
            return location

    logger.warning("FFmpeg not found in common locations")
    return None


def is_apple_podcasts_url(url: str) -> bool:
    """
    Detect if URL is an Apple Podcasts URL

    Args:
        url: URL to check

    Returns:
        True if Apple Podcasts URL, False otherwise
    """
    return bool(re.search(r'podcasts\.apple\.com', url))


# extract_podcast_id() removed — duplicated by ApplePodcastsHandler.extract_podcast_id()
