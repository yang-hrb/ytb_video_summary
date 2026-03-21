import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, Optional

import requests

from config import config
from .utils import create_summary_header, format_duration

logger = logging.getLogger(__name__)


class Summarizer:
    """Use OpenRouter for text summarization"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.openrouter_key = api_key or config.OPENROUTER_API_KEY
        self.model = model or config.OPENROUTER_MODEL

        self.openrouter_models = [
            config.MODEL_PRIORITY_1,
            config.MODEL_PRIORITY_2,
            config.MODEL_PRIORITY_3,
            config.MODEL_FALLBACK,
        ]

        if not any(self.openrouter_models):
            self.openrouter_models = [self.model]

        self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"

    @staticmethod
    def clean_srt_content(content: str) -> str:
        """Strip sequence numbers, timecodes and blank lines from SRT content."""
        lines = content.splitlines()
        cleaned = []
        timestamp_pattern = re.compile(r"^\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}$")

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            if line.isdigit():
                continue
            if timestamp_pattern.match(line) or "-->" in line:
                continue
            cleaned.append(line)

        return " ".join(cleaned)

    def create_prompt(self, transcript: str, style: str = "detailed", language: str = "en") -> str:
        transcript = self.clean_srt_content(transcript)

        if language == "zh":
            if style == "brief":
                prompt = f"""请简明扼要地总结以下视频内容：

1. 用2-3句话概括核心内容
2. 列出3-5个关键要点
3. 提取1-2条核心见解

视频文字稿：
{transcript}

请按以下格式输出：

## 📝 内容概要
[简要总结]

## 🎯 关键要点
- 要点1
- 要点2
- 要点3

## 💡 核心见解
[深度洞察]
"""
            else:
                prompt = f"""请详细总结以下视频内容：

1. 用3-5句话概括核心内容
2. 列出所有重要要点（5-10条）
3. 如果可能，创建时间线总结
4. 提供深入的分析和见解

视频文字稿：
{transcript}

请按以下格式输出：

## 📝 内容概要
[详细总结]

## 🎯 关键要点
- 要点1
- 要点2
- 要点3
[更多要点...]

## ⏱ 时间线
- 00:00 - 主题1
- 05:30 - 主题2
[更多时间戳...]

## 💡 核心见解
[深入分析]

## 🔍 补充说明
[其他重要信息]
"""
        else:
            if style == "brief":
                prompt = f"""Please summarize the following video content concisely:

1. Summarize the core content in 2-3 sentences
2. List 3-5 key points
3. Extract 1-2 core insights

Video transcript:
{transcript}

Please output in the following format:

## 📝 Content Summary
[Brief summary]

## 🎯 Key Points
- Point 1
- Point 2
- Point 3

## 💡 Core Insights
[Deep insights]
"""
            else:
                prompt = f"""Please summarize the following video content in detail:

1. Summarize the core content in 3-5 sentences
2. List all important points (5-10 items)
3. Create a timeline summary if possible
4. Provide in-depth analysis and insights

Video transcript:
{transcript}

Please output in the following format:

## 📝 Content Summary
[Detailed summary]

## 🎯 Key Points
- Point 1
- Point 2
- Point 3
[More points...]

## ⏱ Timeline
- 00:00 - Topic 1
- 05:30 - Topic 2
[More timestamps...]

## 💡 Core Insights
[In-depth analysis]

## 🔍 Additional Notes
[Other important information]
"""

        return prompt

    def summarize(self, transcript: str, style: str = "detailed", language: str = "en", max_tokens: int = 8000, custom_prompt: Optional[str] = None) -> tuple:
        if custom_prompt:
            transcript_clean = self.clean_srt_content(transcript)
            prompt = f"{custom_prompt}\n\nVideo transcript:\n{transcript_clean}"
        else:
            prompt = self.create_prompt(transcript, style, language)
        return self._summarize_with_waterfall(prompt, max_tokens)

    def _is_retryable_http_error(self, status_code: Optional[int]) -> bool:
        if status_code is None:
            return True
        return status_code == 429 or 500 <= status_code < 600

    def _build_openrouter_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ytb_video_summary",
            "X-Title": "YouTube Video Summarizer"
        }

    def _summarize_with_waterfall(self, prompt: str, max_tokens: int) -> tuple:
        if self.openrouter_key:
            for model_name in self.openrouter_models:
                if not model_name:
                    continue

                for attempt in range(1, 4):
                    try:
                        summary = self._summarize_openrouter(prompt, max_tokens, model_name)
                        return summary, model_name
                    except requests.exceptions.RequestException as e:
                        status_code = getattr(getattr(e, "response", None), "status_code", None)
                        retryable = self._is_retryable_http_error(status_code)
                        if retryable and attempt < 3:
                            backoff_seconds = 2 ** attempt
                            logger.warning(
                                "OpenRouter failed for model %s (attempt %s/3, status=%s). Retrying in %ss.",
                                model_name,
                                attempt,
                                status_code,
                                backoff_seconds,
                            )
                            time.sleep(backoff_seconds)
                            continue

                        if retryable:
                            logger.warning("OpenRouter model %s exhausted retries, switching to next model.", model_name)
                            break
                        raise
                    except Exception:
                        logger.warning("OpenRouter model %s parsing failed, switching model.", model_name)
                        break

        raise RuntimeError("All OpenRouter models failed")

    def _summarize_openrouter(self, prompt: str, max_tokens: int, model_name: str) -> str:
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }

        logger.info("Sending request to OpenRouter API (model: %s)...", model_name)
        response = requests.post(
            self.openrouter_url,
            headers=self._build_openrouter_headers(),
            json=payload,
            timeout=60,
        )
        response.raise_for_status()

        result = response.json()
        summary = result['choices'][0]['message']['content']
        logger.info("Summary generated successfully")
        return summary.strip()

    def save_summary(self, summary: str, output_path: Path,
                     video_info: Optional[Dict] = None, video_id: Optional[str] = None,
                     video_url: Optional[str] = None, model_name: Optional[str] = None):
        content = ""

        if video_info:
            title = video_info.get('title', 'Unknown')
            duration = format_duration(video_info.get('duration', 0))
            content = create_summary_header(title, duration)

        content += summary

        if video_id or video_url or model_name:
            content += "\n\n---\n\n## 📎 Reference Information\n\n"
            if video_id:
                content += f"**Video ID**: `{video_id}`\n\n"
            if video_url:
                content += f"**Video Link**: {video_url}\n\n"
            if model_name:
                content += f"**AI Model**: `{model_name}`\n"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Summary saved: {output_path}")


def summarize_transcript(transcript: str, video_id: str,
                        video_info: Optional[Dict] = None,
                        style: str = "detailed",
                        language: str = "en",
                        video_url: Optional[str] = None) -> Dict:
    from .utils import create_report_filename

    uploader = video_info.get('uploader', '') if video_info else ''
    
    from .prompt_selector import PromptSelector
    selector = PromptSelector(config.BASE_DIR / 'config')
    selection = selector.select_for_uploader(uploader)
    custom_prompt = selection.get('prompt_text')

    summarizer = Summarizer()
    summary, model_used = summarizer.summarize(
        transcript, style=style, language=language, custom_prompt=custom_prompt
    )

    summary_path = config.SUMMARY_DIR / f"{video_id}_summary.md"
    summarizer.save_summary(summary, summary_path, video_info, video_id, video_url, model_used)

    report_path = None

    if video_info and video_info.get('title'):
        is_local_mp3 = (uploader == 'Local Audio')

        report_filename = create_report_filename(
            video_info['title'],
            uploader=uploader,
            upload_date=video_info.get('upload_date', ''),
            summary=summary,
            is_local_mp3=is_local_mp3
        )
        report_path = config.REPORT_DIR / report_filename

        summarizer.save_summary(summary, report_path, video_info, video_id, video_url, model_used)
        logger.info(f"Report saved: {report_path}")

    return {
        'summary_path': summary_path,
        'report_path': report_path,
        'prompt_info': selection,
        'model_used': model_used
    }
