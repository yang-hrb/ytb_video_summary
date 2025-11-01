import whisper
import os
from pathlib import Path
from typing import Optional, List, Dict
import logging

from config import config
from .utils import format_timestamp, find_ffmpeg_location

logger = logging.getLogger(__name__)


class Transcriber:
    """Use Whisper for audio transcription"""

    def __init__(self, model_name: Optional[str] = None, language: Optional[str] = None):
        """
        Initialize transcriber

        Args:
            model_name: Whisper model name (tiny/base/small/medium/large)
            language: Language code (zh/en/auto)
        """
        self.model_name = model_name or config.WHISPER_MODEL
        self.language = language if language != 'auto' else None
        self.model = None

    def load_model(self):
        """Load Whisper model"""
        if self.model is None:
            # Ensure FFmpeg is in PATH (required by Whisper)
            ffmpeg_location = find_ffmpeg_location()
            if ffmpeg_location and ffmpeg_location not in os.environ.get('PATH', ''):
                os.environ['PATH'] = f"{ffmpeg_location}{os.pathsep}{os.environ.get('PATH', '')}"
                logger.info(f"Added FFmpeg to PATH: {ffmpeg_location}")

            logger.info(f"Loading Whisper model: {self.model_name}")
            self.model = whisper.load_model(self.model_name)
            logger.info("Model loaded successfully")

    def transcribe_audio(self, audio_path: Path, verbose: bool = True) -> Dict:
        """
        Transcribe audio file

        Args:
            audio_path: Path to audio file
            verbose: Whether to show progress

        Returns:
            Dictionary containing transcription results
        """
        self.load_model()

        logger.info(f"Transcribing audio: {audio_path}")

        # Whisper transcription options
        transcribe_opts = {
            'verbose': verbose,
            'fp16': False,  # Set to False when running on CPU
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
        Save transcription result as SRT format

        Args:
            result: Whisper transcription result
            output_path: Output file path
        """
        segments = result.get('segments', [])

        with open(output_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(segments, start=1):
                # SRT sequence number
                f.write(f"{i}\n")

                # Timestamp
                start_time = format_timestamp(segment['start'])
                end_time = format_timestamp(segment['end'])
                f.write(f"{start_time} --> {end_time}\n")

                # Text content
                text = segment['text'].strip()
                f.write(f"{text}\n\n")

        logger.info(f"SRT file saved: {output_path}")

    def save_as_txt(self, result: Dict, output_path: Path):
        """
        Save transcription result as plain text

        Args:
            result: Whisper transcription result
            output_path: Output file path
        """
        text = result.get('text', '')

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text.strip())

        logger.info(f"Text file saved: {output_path}")

    def get_transcript_text(self, result: Dict) -> str:
        """
        Extract plain text from transcription result

        Args:
            result: Whisper transcription result

        Returns:
            Transcript text
        """
        return result.get('text', '').strip()


def transcribe_video_audio(audio_path: Path, video_id: str,
                           save_srt: bool = True, save_txt: bool = False) -> str:
    """
    Transcribe video audio (convenience function)

    Args:
        audio_path: Path to audio file
        video_id: Video ID
        save_srt: Whether to save SRT file
        save_txt: Whether to save plain text file

    Returns:
        Transcript text
    """
    transcriber = Transcriber()
    result = transcriber.transcribe_audio(audio_path)

    # Save files
    if save_srt:
        srt_path = config.TRANSCRIPT_DIR / f"{video_id}_transcript.srt"
        transcriber.save_as_srt(result, srt_path)

    if save_txt:
        txt_path = config.TRANSCRIPT_DIR / f"{video_id}_transcript.txt"
        transcriber.save_as_txt(result, txt_path)

    return transcriber.get_transcript_text(result)


def read_subtitle_file(subtitle_path: Path) -> str:
    """
    Read subtitle file and extract plain text

    Args:
        subtitle_path: Path to subtitle file

    Returns:
        Extracted text content
    """
    with open(subtitle_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Filter out sequence numbers and timestamps, keep only text
    text_lines = []
    for line in lines:
        line = line.strip()
        # Skip empty lines, sequence numbers, and timestamps
        if not line or line.isdigit() or '-->' in line:
            continue
        text_lines.append(line)

    return ' '.join(text_lines)
