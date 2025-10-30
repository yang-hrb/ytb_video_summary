import os
import re
import logging
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        max_length: 最大长度
        
    Returns:
        清理后的文件名
    """
    # 移除非法字符
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # 移除多余的空格
    filename = re.sub(r'\s+', ' ', filename).strip()
    # 限制长度
    if len(filename) > max_length:
        filename = filename[:max_length]
    return filename


def create_report_filename(title: str) -> str:
    """
    创建报告文件名：时间戳_视频标题.md
    
    Args:
        title: 视频标题
        
    Returns:
        格式化的文件名
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    clean_title = sanitize_filename(title, max_length=100)
    return f"{timestamp}_{clean_title}.md"


def format_duration(seconds: int) -> str:
    """
    将秒数转换为可读的时长格式
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化的时长 (HH:MM:SS 或 MM:SS)
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
    将秒数转换为 SRT 时间戳格式
    
    Args:
        seconds: 秒数
        
    Returns:
        SRT 格式时间戳 (HH:MM:SS,mmm)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def clean_temp_files(temp_dir: Path, keep_pattern: Optional[str] = None):
    """
    清理临时文件
    
    Args:
        temp_dir: 临时文件目录
        keep_pattern: 保留文件的模式（正则表达式）
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
    获取文件大小（MB）
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件大小（MB）
    """
    if not file_path.exists():
        return 0.0
    return file_path.stat().st_size / (1024 * 1024)


def extract_video_id(url: str) -> Optional[str]:
    """
    从 YouTube URL 中提取视频 ID
    
    Args:
        url: YouTube URL
        
    Returns:
        视频 ID 或 None
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


def create_summary_header(title: str, duration: str, timestamp: Optional[str] = None) -> str:
    """
    创建总结文件的标题头部
    
    Args:
        title: 视频标题
        duration: 视频时长
        timestamp: 生成时间戳
        
    Returns:
        Markdown 格式的头部
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    header = f"""# {title}

**时长**: {duration}  
**生成时间**: {timestamp}

---

"""
    return header


def ensure_dir_exists(directory: Path):
    """
    确保目录存在，不存在则创建

    Args:
        directory: 目录路径
    """
    directory.mkdir(parents=True, exist_ok=True)


def find_ffmpeg_location() -> Optional[str]:
    """
    查找 FFmpeg 可执行文件位置

    Returns:
        FFmpeg 目录路径，如果未找到则返回 None
    """
    # 1. 检查环境变量
    ffmpeg_env = os.getenv('FFMPEG_LOCATION')
    if ffmpeg_env and Path(ffmpeg_env).exists():
        logger.info(f"Using FFmpeg from environment variable: {ffmpeg_env}")
        return ffmpeg_env

    # 2. 检查 PATH 中的 ffmpeg
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        ffmpeg_dir = str(Path(ffmpeg_path).parent)
        logger.info(f"Found FFmpeg in PATH: {ffmpeg_dir}")
        return ffmpeg_dir

    # 3. 检查常见的安装位置
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
