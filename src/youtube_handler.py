import yt_dlp
from pathlib import Path
from typing import Dict, Optional
import logging

from config import config
from .utils import sanitize_filename, extract_video_id, find_ffmpeg_location

logger = logging.getLogger(__name__)


class YouTubeHandler:
    """处理 YouTube 视频下载和元数据提取"""
    
    def __init__(self, cookies_file: Optional[str] = None):
        """
        初始化 YouTube 处理器
        
        Args:
            cookies_file: cookies.txt 文件路径（用于会员视频）
        """
        self.cookies_file = cookies_file
        self.temp_dir = config.TEMP_DIR
        
    def get_video_info(self, url: str) -> Dict:
        """
        获取视频信息（不下载）
        
        Args:
            url: YouTube 视频 URL
            
        Returns:
            包含视频信息的字典
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
        下载视频音频
        
        Args:
            url: YouTube 视频 URL
            video_id: 视频 ID（可选，用于文件命名）
            
        Returns:
            下载的音频文件路径
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

        # 添加 FFmpeg 位置（如果找到）
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
        下载视频字幕（如果存在）
        
        Args:
            url: YouTube 视频 URL
            video_id: 视频 ID
            lang: 字幕语言代码
            
        Returns:
            字幕文件路径，如果不存在则返回 None
        """
        if video_id is None:
            video_id = extract_video_id(url)
        
        output_path = config.TRANSCRIPT_DIR / f"{video_id}"
        
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': [lang, 'en'],  # 尝试多种语言
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
            
            # 查找下载的字幕文件
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


def process_youtube_video(url: str, cookies_file: Optional[str] = None) -> Dict:
    """
    处理 YouTube 视频（便捷函数）
    
    Args:
        url: YouTube 视频 URL
        cookies_file: cookies.txt 文件路径
        
    Returns:
        包含视频信息和文件路径的字典
    """
    handler = YouTubeHandler(cookies_file)
    
    # 获取视频信息
    info = handler.get_video_info(url)
    video_id = info['id']
    
    # 尝试下载字幕
    subtitle_path = handler.download_subtitles(url, video_id)
    
    # 如果没有字幕，下载音频用于转录
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
