"""Audio transcription with dual-backend support.

Backends:
  - openai  : original openai-whisper (CPU / non-Apple-Silicon)
  - mlx     : mlx-whisper (Apple Silicon, significantly faster via Metal)

The backend is chosen automatically via ``config.resolve_whisper_backend()``
(WHISPER_BACKEND env-var, defaults to 'auto' which picks 'mlx' on arm64 macOS).

Public API (``Transcriber``, module-level helpers) is unchanged.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict
import logging

from config import config
from .utils import format_timestamp, find_ffmpeg_location

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Backend adapters
# ---------------------------------------------------------------------------

class _OpenAIWhisperBackend:
    """Wraps the original ``openai-whisper`` library."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    def load(self) -> None:
        if self._model is None:
            import whisper  # noqa: PLC0415
            logger.info("Loading openai-whisper model: %s", self.model_name)
            self._model = whisper.load_model(self.model_name)
            logger.info(
                "Whisper backend: openai (openai-whisper, model=%s)", self.model_name
            )

    def transcribe(self, audio_path: str, language: Optional[str], verbose: bool) -> Dict:
        self.load()
        opts: Dict = {"verbose": verbose, "fp16": False}
        if language:
            opts["language"] = language
        return self._model.transcribe(audio_path, **opts)


class _MLXWhisperBackend:
    """Wraps the ``mlx-whisper`` library (Apple Silicon / Metal)."""

    # Official Whisper model name → mlx-community HuggingFace repo
    MODEL_MAP: Dict[str, str] = {
        "tiny":   "mlx-community/whisper-tiny-mlx",
        "base":   "mlx-community/whisper-base-mlx",
        "small":  "mlx-community/whisper-small-mlx",
        "medium": "mlx-community/whisper-medium-mlx",
        "large":  "mlx-community/whisper-large-v3-mlx",
        "turbo":  "mlx-community/whisper-turbo",
    }

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.hf_repo = self.MODEL_MAP.get(model_name, f"mlx-community/whisper-{model_name}-mlx")
        self._mlx_whisper = None

    def load(self) -> None:
        if self._mlx_whisper is None:
            try:
                import mlx_whisper  # noqa: PLC0415
                self._mlx_whisper = mlx_whisper
                logger.info(
                    "Whisper backend: mlx (mlx-whisper, Apple Silicon optimized, repo=%s)",
                    self.hf_repo,
                )
            except ImportError:
                logger.warning(
                    "mlx-whisper not installed; falling back to openai-whisper"
                )
                self._mlx_whisper = None

    def transcribe(self, audio_path: str, language: Optional[str], verbose: bool) -> Dict:
        self.load()
        if self._mlx_whisper is None:
            # Graceful fallback: use openai backend
            fallback = _OpenAIWhisperBackend(self.model_name)
            return fallback.transcribe(audio_path, language, verbose)

        opts: Dict = {"verbose": verbose, "path_or_hf_repo": self.hf_repo}
        if language:
            opts["language"] = language
        return self._mlx_whisper.transcribe(audio_path, **opts)


def _create_backend(model_name: str) -> "_OpenAIWhisperBackend | _MLXWhisperBackend":
    """Factory: return the appropriate backend based on config."""
    backend_name = config.resolve_whisper_backend()
    if backend_name == "mlx":
        return _MLXWhisperBackend(model_name)
    return _OpenAIWhisperBackend(model_name)


# ---------------------------------------------------------------------------
# Public Transcriber class (API unchanged)
# ---------------------------------------------------------------------------

class Transcriber:
    """Use Whisper for audio transcription (backend-agnostic)."""

    def __init__(self, model_name: Optional[str] = None, language: Optional[str] = None):
        """
        Initialize transcriber.

        Args:
            model_name: Whisper model name (tiny/base/small/medium/large/turbo)
            language: Language code (zh/en/auto)
        """
        self.model_name = model_name or config.WHISPER_MODEL
        self.language = language if language != 'auto' else None
        self._backend = _create_backend(self.model_name)

    def load_model(self):
        """Load (pre-warm) the Whisper model."""
        # Ensure FFmpeg is in PATH (required by openai-whisper)
        ffmpeg_location = find_ffmpeg_location()
        if ffmpeg_location and ffmpeg_location not in os.environ.get('PATH', ''):
            os.environ['PATH'] = f"{ffmpeg_location}{os.pathsep}{os.environ.get('PATH', '')}"
            logger.info("Added FFmpeg to PATH: %s", ffmpeg_location)
        self._backend.load()

    def transcribe_audio(self, audio_path: Path, verbose: bool = True) -> Dict:
        """
        Transcribe audio file.

        Args:
            audio_path: Path to audio file
            verbose: Whether to show progress

        Returns:
            Dictionary containing transcription results
        """
        # Ensure FFmpeg is findable
        ffmpeg_location = find_ffmpeg_location()
        if ffmpeg_location and ffmpeg_location not in os.environ.get('PATH', ''):
            os.environ['PATH'] = f"{ffmpeg_location}{os.pathsep}{os.environ.get('PATH', '')}"

        logger.info("Transcribing audio: %s", audio_path)
        try:
            result = self._backend.transcribe(str(audio_path), self.language, verbose)
            logger.info("Transcription completed")
            return result
        except Exception as e:
            logger.error("Transcription failed: %s", e)
            raise

    def save_as_srt(self, result: Dict, output_path: Path):
        """
        Save transcription result as SRT format.

        Args:
            result: Whisper transcription result
            output_path: Output file path
        """
        segments = result.get('segments', [])

        with open(output_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(segments, start=1):
                f.write(f"{i}\n")
                start_time = format_timestamp(segment['start'])
                end_time = format_timestamp(segment['end'])
                f.write(f"{start_time} --> {end_time}\n")
                text = segment['text'].strip()
                f.write(f"{text}\n\n")

        logger.info("SRT file saved: %s", output_path)

    # save_as_txt() removed — not used in the current pipeline

    def get_transcript_text(self, result: Dict) -> str:
        """
        Extract plain text from transcription result.

        Args:
            result: Whisper transcription result

        Returns:
            Transcript text
        """
        return result.get('text', '').strip()


# ---------------------------------------------------------------------------
# Module-level convenience helpers (API unchanged)
# ---------------------------------------------------------------------------

def transcribe_video_audio(audio_path: Path, video_id: str,
                           save_srt: bool = True, save_txt: bool = False) -> tuple:
    """
    Transcribe video audio (convenience function).

    Args:
        audio_path: Path to audio file
        video_id: Video ID
        save_srt: Whether to save SRT file
        save_txt: Whether to save plain text file (ignored — txt output removed)

    Returns:
        Tuple of (transcript_text, detected_language)
    """
    transcriber = Transcriber()
    result = transcriber.transcribe_audio(audio_path)

    if save_srt:
        srt_path = config.TRANSCRIPT_DIR / f"{video_id}_transcript.srt"
        transcriber.save_as_srt(result, srt_path)

    detected_language = result.get('language', 'en')
    return transcriber.get_transcript_text(result), detected_language


def detect_language_from_text(text: str) -> str:
    """
    Detect language from text content (simple heuristic).

    Args:
        text: Text to analyze

    Returns:
        Detected language code ('zh' or 'en')
    """
    chinese_char_count = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
    if len(text) > 0 and (chinese_char_count / len(text)) > 0.1:
        return 'zh'
    return 'en'


def read_subtitle_file(subtitle_path: Path) -> tuple:
    """
    Read subtitle file and extract plain text.

    Args:
        subtitle_path: Path to subtitle file

    Returns:
        Tuple of (extracted_text, detected_language)
    """
    with open(subtitle_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    text_lines = []
    for line in lines:
        line = line.strip()
        if not line or line.isdigit() or '-->' in line:
            continue
        text_lines.append(line)

    text = ' '.join(text_lines)
    language = detect_language_from_text(text)
    return text, language
