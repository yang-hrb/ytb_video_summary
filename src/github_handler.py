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

        # Read file content (detect binary vs text)
        # Binary files: .db, .sqlite, .bin, etc.
        binary_extensions = {'.db', '.sqlite', '.sqlite3', '.bin', '.zip', '.tar', '.gz'}
        is_binary = file_path.suffix.lower() in binary_extensions

        if is_binary:
            with open(file_path, 'rb') as f:
                content_bytes = f.read()
            content_base64 = base64.b64encode(content_bytes).decode('utf-8')
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
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


def upload_logs_to_github(current_log_file: Optional[Path] = None) -> dict:
    """
    Upload current session log files and database to GitHub repository

    Args:
        current_log_file: Path to the current log file (from this session)

    Returns:
        Dictionary with upload results: {'db_url': url, 'log_files': [urls]}
    """
    # Check if GitHub is configured
    if not config.GITHUB_TOKEN or not config.GITHUB_REPO:
        logger.info("GitHub integration not configured, skipping log upload")
        return {'db_url': None, 'log_files': []}

    results = {'db_url': None, 'log_files': []}

    try:
        handler = GitHubHandler()

        # Upload database file (contains all history)
        db_path = config.LOG_DIR / "run_track.db"
        if db_path.exists():
            logger.info("Uploading run tracking database to GitHub...")
            remote_db_path = "logs/run_track.db"
            try:
                db_url = handler.upload_file(
                    db_path,
                    remote_db_path,
                    commit_message="Update run tracking database"
                )
                results['db_url'] = db_url
                logger.info(f"Database uploaded: {db_url}")
            except Exception as e:
                logger.error(f"Failed to upload database: {e}")

        # Upload only the current session's log files
        log_files_to_upload = []

        # Add current log file if provided
        if current_log_file and current_log_file.exists():
            log_files_to_upload.append(current_log_file)

            # Get the creation time of current log file to find failure logs from this session
            log_creation_time = current_log_file.stat().st_mtime

            # Find failure logs created during this session
            for failure_file in config.LOG_DIR.glob("failures_*.txt"):
                # Only upload failure files created during or after this session started
                if failure_file.stat().st_mtime >= log_creation_time:
                    log_files_to_upload.append(failure_file)

        if log_files_to_upload:
            logger.info(f"Uploading {len(log_files_to_upload)} log file(s) from current session...")
            for log_file in log_files_to_upload:
                try:
                    remote_log_path = f"logs/{log_file.name}"
                    log_url = handler.upload_file(
                        log_file,
                        remote_log_path,
                        commit_message=f"Add log: {log_file.name}"
                    )
                    results['log_files'].append({'file': log_file.name, 'url': log_url})
                    logger.info(f"Log file uploaded: {log_file.name}")
                except Exception as e:
                    logger.error(f"Failed to upload log file {log_file.name}: {e}")

        return results

    except Exception as e:
        logger.error(f"Failed to upload logs to GitHub: {e}")
        return results
