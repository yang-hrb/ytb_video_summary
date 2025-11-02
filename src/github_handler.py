import requests
import base64
from pathlib import Path
from typing import Optional
import logging

from config import config

logger = logging.getLogger(__name__)


class GitHubHandler:
    """Handle GitHub API operations for uploading report files"""

    def __init__(self, token: Optional[str] = None, repo: Optional[str] = None, branch: str = "main"):
        """
        Initialize GitHub handler

        Args:
            token: GitHub Personal Access Token
            repo: Repository in format "owner/repo"
            branch: Target branch name (default: main)
        """
        self.token = token or config.GITHUB_TOKEN
        self.repo = repo or config.GITHUB_REPO
        self.branch = branch or config.GITHUB_BRANCH
        self.api_url = "https://api.github.com"

        if not self.token:
            raise ValueError("GitHub token is required")
        if not self.repo:
            raise ValueError("GitHub repository is required (format: owner/repo)")

    def upload_file(self, file_path: Path, remote_path: str, commit_message: Optional[str] = None, skip_existing: bool = False) -> Optional[str]:
        """
        Upload a file to GitHub repository

        Args:
            file_path: Local file path
            remote_path: Path in repository (e.g., "reports/summary.md")
            commit_message: Commit message (auto-generated if not provided)
            skip_existing: If True, skip upload if file already exists in repo

        Returns:
            File URL in the repository, or None if skipped
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Encode content to base64
        content_base64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')

        # Auto-generate commit message if not provided
        if not commit_message:
            commit_message = f"Add report: {file_path.name}"

        # Check if file already exists
        file_url = f"{self.api_url}/repos/{self.repo}/contents/{remote_path}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

        sha = None
        file_exists = False
        try:
            response = requests.get(file_url, headers=headers)
            if response.status_code == 200:
                file_exists = True
                sha = response.json().get('sha')

                # If skip_existing is True, skip upload
                if skip_existing:
                    logger.info(f"File already exists, skipping: {remote_path}")
                    return None

                logger.info(f"File exists, will update: {remote_path}")
        except Exception as e:
            logger.debug(f"File does not exist yet: {e}")

        # Prepare payload
        payload = {
            "message": commit_message,
            "content": content_base64,
            "branch": self.branch
        }

        if sha:
            payload["sha"] = sha

        # Upload file
        try:
            logger.info(f"Uploading to GitHub: {remote_path}")
            response = requests.put(file_url, headers=headers, json=payload)
            response.raise_for_status()

            result = response.json()
            html_url = result['content']['html_url']

            logger.info(f"File uploaded successfully: {html_url}")
            return html_url

        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub upload failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise


def upload_to_github(file_path: Path, remote_folder: str = "reports") -> Optional[str]:
    """
    Upload a file to GitHub repository (convenience function)

    Args:
        file_path: Local file path
        remote_folder: Folder in repository (default: reports)

    Returns:
        File URL in GitHub, or None if GitHub is not configured
    """
    # Check if GitHub is configured
    if not config.GITHUB_TOKEN or not config.GITHUB_REPO:
        logger.info("GitHub integration not configured, skipping upload")
        return None

    try:
        handler = GitHubHandler()
        remote_path = f"{remote_folder}/{file_path.name}"
        url = handler.upload_file(file_path, remote_path)
        return url
    except Exception as e:
        logger.error(f"Failed to upload to GitHub: {e}")
        return None
