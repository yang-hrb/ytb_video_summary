import requests
from pathlib import Path
from typing import Optional, Dict
import logging
import json

from config import config
from .utils import create_summary_header, format_duration

logger = logging.getLogger(__name__)


class Summarizer:
    """Use OpenRouter API for text summarization"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize summarizer

        Args:
            api_key: OpenRouter API Key
            model: Model name to use (defaults to OPENROUTER_MODEL from config)
        """
        self.api_key = api_key or config.OPENROUTER_API_KEY
        self.model = model or config.OPENROUTER_MODEL
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

        if not self.api_key:
            raise ValueError("OpenRouter API key is required")

    def create_prompt(self, transcript: str, style: str = "detailed", language: str = "en") -> str:
        """
        Create summary prompt

        Args:
            transcript: Video transcript text
            style: Summary style (brief/detailed)
            language: Language for summary output (zh/en)

        Returns:
            Formatted prompt
        """
        if language == "zh":
            # Chinese prompts
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
            else:  # detailed
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
            # English prompts
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
            else:  # detailed
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

    def summarize(self, transcript: str, style: str = "detailed",
                  language: str = "en", max_tokens: int = 2000) -> str:
        """
        Summarize text using AI

        Args:
            transcript: Transcript text
            style: Summary style
            language: Language for summary output (zh/en)
            max_tokens: Maximum token count

        Returns:
            Summary text
        """
        prompt = self.create_prompt(transcript, style, language)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ytb_video_summary",
            "X-Title": "YouTube Video Summarizer"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }

        try:
            logger.info("Sending request to OpenRouter API...")
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()

            result = response.json()
            summary = result['choices'][0]['message']['content']

            logger.info("Summary generated successfully")
            return summary.strip()

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse API response: {e}")
            raise

    def save_summary(self, summary: str, output_path: Path,
                     video_info: Optional[Dict] = None, video_id: Optional[str] = None,
                     video_url: Optional[str] = None):
        """
        Save summary to file

        Args:
            summary: Summary text
            output_path: Output file path
            video_info: Video information (for generating header)
            video_id: Video ID (for adding reference)
            video_url: Video URL (for adding reference)
        """
        content = ""

        # Add header information
        if video_info:
            title = video_info.get('title', 'Unknown')
            duration = format_duration(video_info.get('duration', 0))
            content = create_summary_header(title, duration)

        # Add summary content
        content += summary

        # Add reference information
        if video_id or video_url:
            content += "\n\n---\n\n## 📎 Reference Information\n\n"
            if video_id:
                content += f"**Video ID**: `{video_id}`\n\n"
            if video_url:
                content += f"**Video Link**: {video_url}\n"

        # Save file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Summary saved: {output_path}")


def summarize_transcript(transcript: str, video_id: str,
                        video_info: Optional[Dict] = None,
                        style: str = "detailed",
                        language: str = "en",
                        video_url: Optional[str] = None) -> Dict:
    """
    Summarize transcript text (convenience function)

    Args:
        transcript: Transcript text
        video_id: Video ID
        video_info: Video information
        style: Summary style
        language: Language for summary output (zh/en)
        video_url: Video URL

    Returns:
        Dictionary containing file paths and Notion URL
    """
    from .utils import create_report_filename

    summarizer = Summarizer()
    summary = summarizer.summarize(transcript, style=style, language=language)

    # Save to summaries directory (original functionality)
    summary_path = config.SUMMARY_DIR / f"{video_id}_summary.md"
    summarizer.save_summary(summary, summary_path, video_info)

    # Save to reports directory (new feature with timestamp, uploader, and content title)
    report_path = None

    if video_info and video_info.get('title'):
        # Generate report filename
        uploader = video_info.get('uploader', '')

        # Check if it's a local MP3 file
        is_local_mp3 = (uploader == 'Local Audio')

        report_filename = create_report_filename(
            video_info['title'],
            uploader=uploader,
            summary=summary,
            is_local_mp3=is_local_mp3
        )
        report_path = config.REPORT_DIR / report_filename

        # Save to local file
        summarizer.save_summary(summary, report_path, video_info, video_id, video_url)
        logger.info(f"Report saved: {report_path}")

    return {
        'summary_path': summary_path,
        'report_path': report_path
    }
