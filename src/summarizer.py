import requests
from pathlib import Path
from typing import Optional, Dict
import logging
import json

from config import config
from .utils import create_summary_header, format_duration, format_upload_time

logger = logging.getLogger(__name__)


class Summarizer:
    """Use OpenRouter or Perplexity API for text summarization"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, api_type: Optional[str] = None):
        """
        Initialize summarizer

        Args:
            api_key: API Key (OpenRouter or Perplexity)
            model: Model name to use (defaults to model from config based on API type)
            api_type: API type to use ('OPENROUTER' or 'PERPLEXITY', defaults to config.SUMMARY_API)
        """
        self.api_type = (api_type or config.SUMMARY_API).upper()

        if self.api_type == 'OPENROUTER':
            self.api_key = api_key or config.OPENROUTER_API_KEY
            self.model = model or config.OPENROUTER_MODEL
            self.api_url = "https://openrouter.ai/api/v1/chat/completions"
            if not self.api_key:
                raise ValueError("OpenRouter API key is required")
        elif self.api_type == 'PERPLEXITY':
            self.api_key = api_key or config.PERPLEXITY_API_KEY
            self.model = model or config.PERPLEXITY_MODEL
            self.api_url = "https://api.perplexity.ai"
            if not self.api_key:
                raise ValueError("Perplexity API key is required")
            # Import OpenAI client for Perplexity
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key, base_url=self.api_url)
            except ImportError:
                raise ImportError("openai package is required for Perplexity API. Install it with: pip install openai")
        else:
            raise ValueError(f"Invalid API type: {self.api_type}. Must be 'OPENROUTER' or 'PERPLEXITY'")

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

        if self.api_type == 'OPENROUTER':
            return self._summarize_openrouter(prompt, max_tokens)
        elif self.api_type == 'PERPLEXITY':
            return self._summarize_perplexity(prompt, max_tokens)
        else:
            raise ValueError(f"Unsupported API type: {self.api_type}")

    def _summarize_openrouter(self, prompt: str, max_tokens: int) -> str:
        """
        Summarize using OpenRouter API

        Args:
            prompt: Formatted prompt
            max_tokens: Maximum token count

        Returns:
            Summary text
        """
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
            logger.info(f"Sending request to OpenRouter API (model: {self.model})...")
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
            logger.error(f"OpenRouter API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse OpenRouter API response: {e}")
            raise

    def _summarize_perplexity(self, prompt: str, max_tokens: int) -> str:
        """
        Summarize using Perplexity API

        Args:
            prompt: Formatted prompt
            max_tokens: Maximum token count

        Returns:
            Summary text
        """
        try:
            logger.info(f"Sending request to Perplexity API (model: {self.model})...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )

            summary = response.choices[0].message.content

            logger.info("Summary generated successfully")
            return summary.strip()

        except Exception as e:
            logger.error(f"Perplexity API request failed: {e}")
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
            uploader = video_info.get('uploader')
            upload_time = format_upload_time(
                video_info.get('upload_date'),
                video_info.get('timestamp')
            )
            content = create_summary_header(
                title,
                duration,
                uploader=uploader,
                upload_time=upload_time
            )

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
