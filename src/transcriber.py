import whisper
import os
from pathlib import Path
from typing import Optional, List, Dict
import logging

from config import config
from .utils import format_timestamp, find_ffmpeg_location

logger = logging.getLogger(__name__)


class Transcriber:
    """使用 Whisper 进行音频转录"""
    
    def __init__(self, model_name: Optional[str] = None, language: Optional[str] = None):
        """
        初始化转录器
        
        Args:
            model_name: Whisper 模型名称 (tiny/base/small/medium/large)
            language: 语言代码 (zh/en/auto)
        """
        self.model_name = model_name or config.WHISPER_MODEL
        self.language = language if language != 'auto' else None
        self.model = None
        
    def load_model(self):
        """加载 Whisper 模型"""
        if self.model is None:
            # 确保 FFmpeg 在 PATH 中（Whisper 需要）
            ffmpeg_location = find_ffmpeg_location()
            if ffmpeg_location and ffmpeg_location not in os.environ.get('PATH', ''):
                os.environ['PATH'] = f"{ffmpeg_location}{os.pathsep}{os.environ.get('PATH', '')}"
                logger.info(f"Added FFmpeg to PATH: {ffmpeg_location}")

            logger.info(f"Loading Whisper model: {self.model_name}")
            self.model = whisper.load_model(self.model_name)
            logger.info("Model loaded successfully")
    
    def transcribe_audio(self, audio_path: Path, verbose: bool = True) -> Dict:
        """
        转录音频文件
        
        Args:
            audio_path: 音频文件路径
            verbose: 是否显示进度
            
        Returns:
            包含转录结果的字典
        """
        self.load_model()
        
        logger.info(f"Transcribing audio: {audio_path}")
        
        # Whisper 转录选项
        transcribe_opts = {
            'verbose': verbose,
            'fp16': False,  # 在 CPU 上运行时设置为 False
        }
        
        if self.language:
            transcribe_opts['language'] = self.language
        
        try:
            result = self.model.transcribe(str(audio_path), **transcribe_opts)
            logger.info("Transcription completed")
            return result
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
    def save_as_srt(self, result: Dict, output_path: Path):
        """
        将转录结果保存为 SRT 格式
        
        Args:
            result: Whisper 转录结果
            output_path: 输出文件路径
        """
        segments = result.get('segments', [])
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(segments, start=1):
                # SRT 序号
                f.write(f"{i}\n")
                
                # 时间戳
                start_time = format_timestamp(segment['start'])
                end_time = format_timestamp(segment['end'])
                f.write(f"{start_time} --> {end_time}\n")
                
                # 文本内容
                text = segment['text'].strip()
                f.write(f"{text}\n\n")
        
        logger.info(f"SRT file saved: {output_path}")
    
    def save_as_txt(self, result: Dict, output_path: Path):
        """
        将转录结果保存为纯文本
        
        Args:
            result: Whisper 转录结果
            output_path: 输出文件路径
        """
        text = result.get('text', '')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text.strip())
        
        logger.info(f"Text file saved: {output_path}")
    
    def get_transcript_text(self, result: Dict) -> str:
        """
        从转录结果中提取纯文本
        
        Args:
            result: Whisper 转录结果
            
        Returns:
            转录文本
        """
        return result.get('text', '').strip()


def transcribe_video_audio(audio_path: Path, video_id: str, 
                           save_srt: bool = True, save_txt: bool = False) -> str:
    """
    转录视频音频（便捷函数）
    
    Args:
        audio_path: 音频文件路径
        video_id: 视频 ID
        save_srt: 是否保存 SRT 文件
        save_txt: 是否保存纯文本文件
        
    Returns:
        转录文本
    """
    transcriber = Transcriber()
    result = transcriber.transcribe_audio(audio_path)
    
    # 保存文件
    if save_srt:
        srt_path = config.TRANSCRIPT_DIR / f"{video_id}_transcript.srt"
        transcriber.save_as_srt(result, srt_path)
    
    if save_txt:
        txt_path = config.TRANSCRIPT_DIR / f"{video_id}_transcript.txt"
        transcriber.save_as_txt(result, txt_path)
    
    return transcriber.get_transcript_text(result)


def read_subtitle_file(subtitle_path: Path) -> str:
    """
    读取字幕文件并提取纯文本
    
    Args:
        subtitle_path: 字幕文件路径
        
    Returns:
        提取的文本内容
    """
    with open(subtitle_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 过滤掉序号和时间戳，只保留文本
    text_lines = []
    for line in lines:
        line = line.strip()
        # 跳过空行、序号和时间戳
        if not line or line.isdigit() or '-->' in line:
            continue
        text_lines.append(line)
    
    return ' '.join(text_lines)
