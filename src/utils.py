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
    # Remove illegal characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Remove extra spaces
    filename = re.sub(r'\s+', ' ', filename).strip()
    # Limit length
    if len(filename) > max_length:
        filename = filename[:max_length]
    return filename


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


def create_report_filename(video_title: str, uploader: str = "", summary: str = "") -> str:
    """
    Create report filename: timestamp_uploader_content-title.md

    Args:
        video_title: Video title (used as fallback)
        uploader: Uploader name (first 10 characters)
        summary: Summary content (for generating content-related title)

    Returns:
        Formatted filename
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    # Process uploader name (first 10 characters)
    uploader_part = ""
    if uploader:
        clean_uploader = sanitize_filename(uploader, max_length=10)
        if clean_uploader:
            uploader_part = f"{clean_uploader}_"

    # Extract title from summary content
    if summary:
        content_title = extract_summary_title(summary, max_length=50)
    else:
        # Use video title if no summary
        content_title = sanitize_filename(video_title, max_length=50)

    return f"{timestamp}_{uploader_part}{content_title}.md"


def format_duration(seconds: int) -> str:
    """
    Convert seconds to readable duration format

    Args:
        seconds: Number of seconds

    Returns:
        Formatted duration (HH:MM:SS or MM:SS)
    """
    duration = timedelta(seconds=seconds)
    hours = duration.seconds // 3600
    minutes = (duration.seconds % 3600) // 60
    secs = duration.seconds % 60

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


def clean_temp_files(temp_dir: Path, keep_pattern: Optional[str] = None):
    """
    Clean temporary files

    Args:
        temp_dir: Temporary files directory
        keep_pattern: Pattern for files to keep (regex)
    """
    if not temp_dir.exists():
        return

    for file in temp_dir.iterdir():
        if file.is_file():
            if keep_pattern and re.match(keep_pattern, file.name):
                continue
            try:
                file.unlink()
                logger.info(f"Deleted temp file: {file.name}")
            except Exception as e:
                logger.error(f"Failed to delete {file.name}: {e}")


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


def ensure_dir_exists(directory: Path):
    """
    Ensure directory exists, create if it doesn't

    Args:
        directory: Directory path
    """
    directory.mkdir(parents=True, exist_ok=True)


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
