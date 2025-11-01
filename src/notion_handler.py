import requests
from pathlib import Path
from typing import Optional, Dict
import logging

from config import config

logger = logging.getLogger(__name__)


class NotionHandler:
    """处理 Notion 页面创建和内容上传"""

    def __init__(self, api_key: Optional[str] = None, database_id: Optional[str] = None):
        """
        初始化 Notion 处理器

        Args:
            api_key: Notion Integration Token
            database_id: Notion Database ID
        """
        self.api_key = api_key or config.NOTION_API_KEY
        self.database_id = database_id or config.NOTION_DATABASE_ID
        self.api_url = "https://api.notion.com/v1"
        self.notion_version = "2022-06-28"

        if not self.api_key:
            logger.warning("Notion API key is not set. Notion integration disabled.")
            self.enabled = False
        elif not self.database_id:
            logger.warning("Notion Database ID is not set. Notion integration disabled.")
            self.enabled = False
        else:
            self.enabled = True

    def _get_headers(self) -> Dict[str, str]:
        """
        获取 Notion API 请求头

        Returns:
            请求头字典
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": self.notion_version
        }

    def markdown_to_notion_blocks(self, content: str) -> list:
        """
        将 Markdown 内容转换为 Notion blocks

        Args:
            content: Markdown 格式的内容

        Returns:
            Notion blocks 列表
        """
        blocks = []
        lines = content.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # 空行
            if not line:
                i += 1
                continue

            # 标题
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                text = line.lstrip('#').strip()

                if level == 1:
                    blocks.append({
                        "object": "block",
                        "type": "heading_1",
                        "heading_1": {
                            "rich_text": [{"type": "text", "text": {"content": text}}]
                        }
                    })
                elif level == 2:
                    blocks.append({
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": text}}]
                        }
                    })
                else:
                    blocks.append({
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [{"type": "text", "text": {"content": text}}]
                        }
                    })

            # 列表项
            elif line.startswith('- ') or line.startswith('* '):
                text = line[2:].strip()
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": text}}]
                    }
                })

            # 分隔线
            elif line.startswith('---'):
                blocks.append({
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                })

            # 普通段落
            else:
                # 处理可能的粗体标记
                text = line.replace('**', '')
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": text}}]
                    }
                })

            i += 1

        return blocks

    def create_page(self, title: str, content: str,
                   video_info: Optional[Dict] = None,
                   video_url: Optional[str] = None) -> Optional[str]:
        """
        在 Notion 数据库中创建新页面

        Args:
            title: 页面标题
            content: Markdown 格式的内容
            video_info: 视频信息
            video_url: 视频 URL

        Returns:
            创建的页面 URL，失败时返回 None
        """
        if not self.enabled:
            logger.info("Notion integration is disabled. Skipping...")
            return None

        try:
            # 准备页面属性
            properties = {
                "Name": {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": title}
                        }
                    ]
                }
            }

            # 添加视频 URL 属性（如果数据库有 URL 列）
            if video_url:
                properties["URL"] = {
                    "url": video_url
                }

            # 添加上传者属性（如果数据库有 Uploader 列）
            if video_info and video_info.get('uploader'):
                properties["Uploader"] = {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": video_info['uploader']}
                        }
                    ]
                }

            # 添加时长属性（如果数据库有 Duration 列）
            if video_info and video_info.get('duration'):
                from .utils import format_duration
                duration_str = format_duration(video_info['duration'])
                properties["Duration"] = {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": duration_str}
                        }
                    ]
                }

            # 转换内容为 Notion blocks
            blocks = self.markdown_to_notion_blocks(content)

            # 创建页面
            payload = {
                "parent": {"database_id": self.database_id},
                "properties": properties,
                "children": blocks[:100]  # Notion API 限制一次最多100个blocks
            }

            response = requests.post(
                f"{self.api_url}/pages",
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            page_url = result.get('url', '')

            logger.info(f"Notion page created: {page_url}")
            return page_url

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create Notion page: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating Notion page: {e}")
            return None

    def append_blocks(self, page_id: str, blocks: list) -> bool:
        """
        向已存在的页面追加更多 blocks（用于内容超过100个blocks的情况）

        Args:
            page_id: Notion 页面 ID
            blocks: 要追加的 blocks 列表

        Returns:
            成功返回 True，失败返回 False
        """
        if not self.enabled:
            return False

        try:
            response = requests.patch(
                f"{self.api_url}/blocks/{page_id}/children",
                headers=self._get_headers(),
                json={"children": blocks[:100]},
                timeout=30
            )
            response.raise_for_status()
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to append blocks to Notion page: {e}")
            return False


def save_to_notion(title: str, content: str,
                  video_info: Optional[Dict] = None,
                  video_url: Optional[str] = None) -> Optional[str]:
    """
    保存内容到 Notion（便捷函数）

    Args:
        title: 页面标题
        content: Markdown 内容
        video_info: 视频信息
        video_url: 视频 URL

    Returns:
        Notion 页面 URL，失败时返回 None
    """
    handler = NotionHandler()
    return handler.create_page(title, content, video_info, video_url)
