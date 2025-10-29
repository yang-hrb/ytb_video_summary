import requests
from pathlib import Path
from typing import Optional, Dict
import logging
import json

from config import config
from .utils import create_summary_header, format_duration

logger = logging.getLogger(__name__)


class Summarizer:
    """使用 OpenRouter API 进行文本总结"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "deepseek/deepseek-r1"):
        """
        初始化总结器
        
        Args:
            api_key: OpenRouter API Key
            model: 使用的模型名称
        """
        self.api_key = api_key or config.OPENROUTER_API_KEY
        self.model = model
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        if not self.api_key:
            raise ValueError("OpenRouter API key is required")
    
    def create_prompt(self, transcript: str, style: str = "detailed") -> str:
        """
        创建总结提示词
        
        Args:
            transcript: 视频转录文本
            style: 总结风格 (brief/detailed)
            
        Returns:
            格式化的提示词
        """
        if style == "brief":
            prompt = f"""请用中文总结以下视频内容，要求简洁明了：

1. 用 2-3 句话概括核心内容
2. 列出 3-5 个关键要点
3. 提炼 1-2 个核心见解

视频转录：
{transcript}

请按照以下格式输出：

## 📝 内容摘要
[简短总结]

## 🎯 关键要点
- 要点 1
- 要点 2
- 要点 3

## 💡 核心见解
[深度见解]
"""
        else:  # detailed
            prompt = f"""请用中文详细总结以下视频内容：

1. 用 3-5 句话概括核心内容
2. 列出所有重要要点（5-10 个）
3. 如果可能，创建时间轴摘要
4. 提供深度分析和见解

视频转录：
{transcript}

请按照以下格式输出：

## 📝 内容摘要
[详细总结]

## 🎯 关键要点
- 要点 1
- 要点 2
- 要点 3
[更多要点...]

## ⏱ 时间轴
- 00:00 - 主题 1
- 05:30 - 主题 2
[更多时间点...]

## 💡 核心见解
[深度分析]

## 🔍 补充说明
[其他重要信息]
"""
        
        return prompt
    
    def summarize(self, transcript: str, style: str = "detailed", 
                  max_tokens: int = 2000) -> str:
        """
        使用 AI 总结文本
        
        Args:
            transcript: 转录文本
            style: 总结风格
            max_tokens: 最大 token 数
            
        Returns:
            总结文本
        """
        prompt = self.create_prompt(transcript, style)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
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
                     video_info: Optional[Dict] = None):
        """
        保存总结到文件
        
        Args:
            summary: 总结文本
            output_path: 输出文件路径
            video_info: 视频信息（用于生成头部）
        """
        content = ""
        
        # 添加头部信息
        if video_info:
            title = video_info.get('title', 'Unknown')
            duration = format_duration(video_info.get('duration', 0))
            content = create_summary_header(title, duration)
        
        # 添加总结内容
        content += summary
        
        # 保存文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Summary saved: {output_path}")


def summarize_transcript(transcript: str, video_id: str, 
                        video_info: Optional[Dict] = None,
                        style: str = "detailed") -> str:
    """
    总结转录文本（便捷函数）
    
    Args:
        transcript: 转录文本
        video_id: 视频 ID
        video_info: 视频信息
        style: 总结风格
        
    Returns:
        总结文本
    """
    summarizer = Summarizer()
    summary = summarizer.summarize(transcript, style=style)
    
    # 保存总结
    output_path = config.SUMMARY_DIR / f"{video_id}_summary.md"
    summarizer.save_summary(summary, output_path, video_info)
    
    return summary
