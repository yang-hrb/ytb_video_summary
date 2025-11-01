import requests
from pathlib import Path
from typing import Optional, Dict
import logging

from config import config

logger = logging.getLogger(__name__)


class NotionHandler:
    """Handle Notion page creation and content upload"""

    def __init__(self, api_key: Optional[str] = None, database_id: Optional[str] = None):
        """
        Initialize Notion handler

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
        Get Notion API request headers

        Returns:
            Headers dictionary
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": self.notion_version
        }

    def markdown_to_notion_blocks(self, content: str) -> list:
        """
        Convert Markdown content to Notion blocks

        Args:
            content: Markdown formatted content

        Returns:
            List of Notion blocks
        """
        blocks = []
        lines = content.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Empty line
            if not line:
                i += 1
                continue

            # Heading
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

            # List item
            elif line.startswith('- ') or line.startswith('* '):
                text = line[2:].strip()
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": text}}]
                    }
                })

            # Divider
            elif line.startswith('---'):
                blocks.append({
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                })

            # Regular paragraph
            else:
                # Handle possible bold markers
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
        Create new page in Notion database

        Args:
            title: Page title
            content: Markdown formatted content
            video_info: Video information
            video_url: Video URL

        Returns:
            Created page URL, or None if failed
        """
        if not self.enabled:
            logger.info("Notion integration is disabled. Skipping...")
            return None

        try:
            # Prepare page properties
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

            # Add video URL property (if database has URL column)
            if video_url:
                properties["URL"] = {
                    "url": video_url
                }

            # Add uploader property (if database has Uploader column)
            if video_info and video_info.get('uploader'):
                properties["Uploader"] = {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": video_info['uploader']}
                        }
                    ]
                }

            # Add duration property (if database has Duration column)
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

            # Convert content to Notion blocks
            blocks = self.markdown_to_notion_blocks(content)

            # Create page
            payload = {
                "parent": {"database_id": self.database_id},
                "properties": properties,
                "children": blocks[:100]  # Notion API limits to 100 blocks per request
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
        Append more blocks to an existing page (for content exceeding 100 blocks)

        Args:
            page_id: Notion page ID
            blocks: List of blocks to append

        Returns:
            True if successful, False if failed
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
    Save content to Notion (convenience function)

    Args:
        title: Page title
        content: Markdown content
        video_info: Video information
        video_url: Video URL

    Returns:
        Notion page URL, or None if failed
    """
    handler = NotionHandler()
    return handler.create_page(title, content, video_info, video_url)
