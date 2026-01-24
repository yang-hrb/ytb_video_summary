#!/usr/bin/env python3
"""Convert MP3 audio to SRT subtitles using Whisper."""

import argparse
import json
import logging
from pathlib import Path

from config import config
from src.transcriber import Transcriber
from src.utils import ensure_dir_exists


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert MP3 to SRT using Whisper")
    parser.add_argument("--mp3-path", required=True, help="Path to MP3 file")
    parser.add_argument(
        "--language",
        default="auto",
        help="Language code: zh/en/auto (default: auto)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(config.TRANSCRIPT_DIR),
        help="Output directory for SRT files",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    mp3_path = Path(args.mp3_path).expanduser().resolve()
    if not mp3_path.exists():
        raise FileNotFoundError(f"MP3 not found: {mp3_path}")

    output_dir = Path(args.output_dir)
    ensure_dir_exists(output_dir)

    transcriber = Transcriber(language=args.language)
    result = transcriber.transcribe_audio(mp3_path)

    srt_path = output_dir / f"{mp3_path.stem}.srt"
    transcriber.save_as_srt(result, srt_path)

    response = {
        "srt_path": str(srt_path),
        "detected_language": result.get("language", "unknown"),
    }
    print(json.dumps(response, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
