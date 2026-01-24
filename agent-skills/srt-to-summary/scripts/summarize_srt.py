#!/usr/bin/env python3
"""Summarize SRT transcripts with OpenRouter free models and save Markdown."""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import requests
import yt_dlp

from config import config
from src.transcriber import read_subtitle_file
from src.utils import ensure_dir_exists


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DEFAULT_FREE_MODEL = "meta-llama/llama-3.1-8b-instruct:free"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize SRT subtitles with OpenRouter")
    parser.add_argument("--srt-path", required=True, help="Path to SRT file")
    parser.add_argument("--youtube-url", help="YouTube URL for metadata")
    parser.add_argument("--language", default="zh", choices=["zh", "en"], help="Summary language")
    parser.add_argument("--model", help="OpenRouter model name (free model recommended)")
    parser.add_argument(
        "--output-dir",
        default=str(config.SUMMARY_DIR),
        help="Output directory for summary markdown",
    )
    parser.add_argument("--cookies", help="Path to cookies.txt for membership videos")
    return parser.parse_args()


def fetch_youtube_info(url: str, cookies: Optional[str] = None) -> Dict:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
    }
    if cookies:
        ydl_opts["cookiefile"] = cookies

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    return {
        "video_id": info.get("id"),
        "title": info.get("title"),
        "uploader": info.get("uploader"),
        "upload_date": info.get("upload_date"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "duration": info.get("duration"),
        "webpage_url": info.get("webpage_url"),
    }


def format_upload_date(raw_date: Optional[str]) -> Optional[str]:
    if not raw_date:
        return None
    try:
        return datetime.strptime(raw_date, "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return raw_date


def build_prompt(transcript: str, language: str) -> str:
    if language == "zh":
        return f"""请根据以下字幕内容输出结构化 Markdown 总结：

要求：
1. 用 3-5 句话概括核心内容
2. 列出 5-10 个关键要点
3. 尽可能给出时间线
4. 提供 2-4 条核心见解

字幕内容：
{transcript}

请严格按以下格式输出：

## 📝 内容概要
[详细总结]

## 🎯 关键要点
- 要点1
- 要点2
- 要点3

## ⏱ 时间线
- 00:00 - 主题1
- 05:00 - 主题2

## 💡 核心见解
[深入分析]
"""

    return f"""Please produce a structured Markdown summary based on the subtitles below:

Requirements:
1. Summarize the core content in 3-5 sentences
2. List 5-10 key points
3. Provide a timeline if possible
4. Provide 2-4 core insights

Subtitles:
{transcript}

Output in this exact format:

## 📝 Content Summary
[Detailed summary]

## 🎯 Key Points
- Point 1
- Point 2
- Point 3

## ⏱ Timeline
- 00:00 - Topic 1
- 05:00 - Topic 2

## 💡 Core Insights
[In-depth analysis]
"""


def call_openrouter(prompt: str, model: str) -> str:
    api_key = config.OPENROUTER_API_KEY
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is required")

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4,
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def build_reference_block(info: Dict, youtube_url: Optional[str]) -> str:
    upload_date = format_upload_date(info.get("upload_date"))
    lines = [
        "## 📎 Reference",
        f"- Author: {info.get('uploader') or 'N/A'}",
        f"- Title: {info.get('title') or 'N/A'}",
        f"- Upload Date: {upload_date or 'N/A'}",
        f"- Views: {info.get('view_count') or 'N/A'}",
        f"- Likes: {info.get('like_count') or 'N/A'}",
        f"- Video URL: {info.get('webpage_url') or youtube_url or 'N/A'}",
        f"- Video ID: {info.get('video_id') or 'N/A'}",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    srt_path = Path(args.srt_path).expanduser().resolve()
    if not srt_path.exists():
        raise FileNotFoundError(f"SRT not found: {srt_path}")

    output_dir = Path(args.output_dir)
    ensure_dir_exists(output_dir)

    transcript, _ = read_subtitle_file(srt_path)
    prompt = build_prompt(transcript, args.language)

    model = args.model or config.OPENROUTER_MODEL or DEFAULT_FREE_MODEL
    if ":free" not in model:
        logger.warning("Model does not appear to be free: %s", model)

    summary_text = call_openrouter(prompt, model)

    info: Dict = {}
    if args.youtube_url:
        info = fetch_youtube_info(args.youtube_url, args.cookies)
    else:
        info = {
            "video_id": srt_path.stem,
            "title": srt_path.stem,
        }

    reference_block = build_reference_block(info, args.youtube_url)

    title = info.get("title") or srt_path.stem
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    summary_md = "\n".join([
        f"# {title}",
        "",
        f"**Generated**: {timestamp}",
        f"**Model**: {model}",
        "",
        summary_text,
        "",
        "---",
        "",
        reference_block,
        "",
    ])

    output_path = output_dir / f"{srt_path.stem}_summary.md"
    output_path.write_text(summary_md, encoding="utf-8")

    result = {
        "summary_path": str(output_path),
        "reference": reference_block,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
