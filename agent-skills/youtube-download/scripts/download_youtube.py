#!/usr/bin/env python3
"""Download YouTube subtitles (preferred) or audio (MP3)."""

import argparse
import json
import logging
import shutil
from pathlib import Path

from config import config
from src.youtube_handler import YouTubeHandler
from src.utils import ensure_dir_exists


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download YouTube subtitles or audio")
    parser.add_argument("--url", required=True, help="YouTube video URL")
    parser.add_argument("--cookies", help="Path to cookies.txt for membership videos")
    parser.add_argument("--lang", default="zh", help="Subtitle language (default: zh)")
    parser.add_argument(
        "--output-dir",
        default="output/downloads",
        help="Output directory for downloaded files",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    ensure_dir_exists(output_dir)

    handler = YouTubeHandler(cookies_file=args.cookies)
    info = handler.get_video_info(args.url)
    video_id = info.get("id")
    if not video_id:
        raise ValueError("Unable to extract video ID")

    subtitle_path = handler.download_subtitles(args.url, video_id=video_id, lang=args.lang)
    audio_path = None

    if subtitle_path:
        target_subtitle = output_dir / subtitle_path.name
        shutil.copy2(subtitle_path, target_subtitle)
        subtitle_path = target_subtitle
        logger.info("Subtitle saved to %s", subtitle_path)
    else:
        audio_path = handler.download_audio(args.url, video_id=video_id)
        target_audio = output_dir / audio_path.name
        shutil.move(str(audio_path), target_audio)
        audio_path = target_audio
        logger.info("Audio saved to %s", audio_path)

    result = {
        "video_info": info,
        "subtitle_path": str(subtitle_path) if subtitle_path else None,
        "audio_path": str(audio_path) if audio_path else None,
        "output_dir": str(output_dir),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
