#!/usr/bin/env python3
"""
Upload Markdown Files to GitHub Repository

This script uploads all .md files from a specified folder to a GitHub repository.
Configuration is read from .env file (GITHUB_TOKEN, GITHUB_REPO, GITHUB_BRANCH).

Usage:
    python src/upload_to_github.py <folder_path>
    python src/upload_to_github.py output/reports
    python src/upload_to_github.py output/summaries --remote-folder summaries
"""

import sys
import argparse
from pathlib import Path
import logging
from typing import List

from colorama import init, Fore, Style

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import config
from src.github_handler import GitHubHandler

# Initialize colorama
init(autoreset=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_header():
    """Print script header"""
    header = f"""
{Fore.CYAN}╔═══════════════════════════════════════════════════════════╗
║   GitHub Markdown Uploader v1.0                           ║
║   Upload .md files to GitHub repository                   ║
╚═══════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(header)


def print_success(message: str):
    """Print success message"""
    print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {message}")


def print_error(message: str):
    """Print error message"""
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {message}")


def print_info(message: str):
    """Print info message"""
    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} {message}")


def print_warning(message: str):
    """Print warning message"""
    print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} {message}")


def find_markdown_files(folder_path: Path) -> List[Path]:
    """
    Find all .md files in the specified folder

    Args:
        folder_path: Path to folder to search

    Returns:
        List of Path objects for .md files
    """
    if not folder_path.exists():
        raise FileNotFoundError(f"Folder does not exist: {folder_path}")

    if not folder_path.is_dir():
        raise NotADirectoryError(f"Path is not a folder: {folder_path}")

    md_files = list(folder_path.glob("*.md"))
    return sorted(md_files)


def upload_files(files: List[Path], remote_folder: str = "reports", skip_existing: bool = False) -> dict:
    """
    Upload markdown files to GitHub

    Args:
        files: List of file paths to upload
        remote_folder: Folder in repository to upload to
        skip_existing: If True, skip files that already exist in repo

    Returns:
        Dictionary with upload statistics
    """
    # Validate GitHub configuration
    if not config.GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN not set in .env file")
    if not config.GITHUB_REPO:
        raise ValueError("GITHUB_REPO not set in .env file")

    # Initialize GitHub handler
    handler = GitHubHandler()

    print_info(f"GitHub Repository: {config.GITHUB_REPO}")
    print_info(f"Target Branch: {config.GITHUB_BRANCH}")
    print_info(f"Remote Folder: {remote_folder}")
    if skip_existing:
        print_info(f"Mode: Skip existing files")
    else:
        print_info(f"Mode: Update existing files")
    print()

    # Upload files
    results = {
        'total': len(files),
        'success': 0,
        'skipped': 0,
        'failed': 0,
        'errors': []
    }

    for idx, file_path in enumerate(files, 1):
        print(f"\n{Fore.CYAN}[{idx}/{len(files)}]{Style.RESET_ALL} Uploading: {file_path.name}")

        try:
            remote_path = f"{remote_folder}/{file_path.name}"
            commit_message = f"Upload: {file_path.name}"

            url = handler.upload_file(
                file_path=file_path,
                remote_path=remote_path,
                commit_message=commit_message,
                skip_existing=skip_existing
            )

            if url is None:
                # File was skipped (already exists)
                print_warning(f"Skipped (already exists)")
                results['skipped'] += 1
            else:
                # File was uploaded successfully
                print_success(f"Uploaded successfully")
                print(f"  URL: {Fore.BLUE}{url}{Style.RESET_ALL}")
                results['success'] += 1

        except Exception as e:
            print_error(f"Upload failed: {e}")
            results['failed'] += 1
            results['errors'].append({
                'file': file_path.name,
                'error': str(e)
            })
            logger.exception(f"Failed to upload {file_path}")

    return results


def print_summary(results: dict):
    """Print upload summary"""
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Upload Summary{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

    print(f"Total files: {results['total']}")
    print(f"{Fore.GREEN}Successful: {results['success']}{Style.RESET_ALL}")

    if results.get('skipped', 0) > 0:
        print(f"{Fore.YELLOW}Skipped: {results['skipped']}{Style.RESET_ALL}")

    if results['failed'] > 0:
        print(f"{Fore.RED}Failed: {results['failed']}{Style.RESET_ALL}\n")
        print(f"{Fore.YELLOW}Failed files:{Style.RESET_ALL}")
        for error in results['errors']:
            print(f"  - {error['file']}: {error['error']}")
    elif results.get('skipped', 0) == 0:
        print_success("All files uploaded successfully!")
    else:
        print_success("Upload complete!")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Upload markdown files from a folder to GitHub repository',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload all .md files from output/reports to 'reports' folder in GitHub
  python src/upload_to_github.py output/reports

  # Upload to a different remote folder
  python src/upload_to_github.py output/summaries --remote-folder summaries

  # Upload from current directory
  python src/upload_to_github.py .

Configuration:
  This script reads GitHub credentials from .env file:
  - GITHUB_TOKEN: Personal Access Token with 'repo' permissions
  - GITHUB_REPO: Repository name in format 'owner/repo'
  - GITHUB_BRANCH: Target branch (default: main)

Setup:
  1. Copy .env.example to .env
  2. Add your GitHub token and repository details
  3. Run this script with the folder path
        """
    )

    parser.add_argument(
        'folder',
        type=str,
        help='Path to folder containing .md files'
    )

    parser.add_argument(
        '--remote-folder',
        type=str,
        default='reports',
        help='Folder in GitHub repository to upload to (default: reports)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be uploaded without actually uploading'
    )

    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip files that already exist in the repository'
    )

    args = parser.parse_args()

    # Print header
    print_header()

    try:
        # Convert folder path
        folder_path = Path(args.folder)

        print_info(f"Local folder: {folder_path.absolute()}")

        # Find markdown files
        print_info("Scanning for .md files...\n")
        md_files = find_markdown_files(folder_path)

        if not md_files:
            print_warning(f"No .md files found in {folder_path}")
            sys.exit(0)

        print(f"Found {Fore.GREEN}{len(md_files)}{Style.RESET_ALL} markdown files:\n")
        for file_path in md_files:
            print(f"  - {file_path.name}")

        # Dry run mode
        if args.dry_run:
            print_info("\nDry run mode - no files will be uploaded")
            print_info(f"Files would be uploaded to: {config.GITHUB_REPO}/{args.remote_folder}")
            sys.exit(0)

        # Confirm upload
        print(f"\n{Fore.YELLOW}Ready to upload {len(md_files)} files to GitHub{Style.RESET_ALL}")
        print(f"Repository: {Fore.CYAN}{config.GITHUB_REPO}{Style.RESET_ALL}")
        print(f"Branch: {Fore.CYAN}{config.GITHUB_BRANCH}{Style.RESET_ALL}")
        print(f"Remote folder: {Fore.CYAN}{args.remote_folder}{Style.RESET_ALL}")
        if args.skip_existing:
            print(f"Mode: {Fore.YELLOW}Skip existing files{Style.RESET_ALL}")

        response = input(f"\n{Fore.YELLOW}Continue? [y/N]:{Style.RESET_ALL} ")
        if response.lower() not in ['y', 'yes']:
            print_info("Upload cancelled by user")
            sys.exit(0)

        # Upload files
        print(f"\n{Fore.CYAN}Starting upload...{Style.RESET_ALL}")
        results = upload_files(md_files, args.remote_folder, skip_existing=args.skip_existing)

        # Print summary
        print_summary(results)

        # Exit code
        sys.exit(0 if results['failed'] == 0 else 1)

    except FileNotFoundError as e:
        print_error(str(e))
        sys.exit(1)
    except NotADirectoryError as e:
        print_error(str(e))
        sys.exit(1)
    except ValueError as e:
        print_error(str(e))
        print_info("\nPlease configure GitHub settings in .env file:")
        print("  GITHUB_TOKEN=your_personal_access_token")
        print("  GITHUB_REPO=owner/repository")
        print("  GITHUB_BRANCH=main")
        sys.exit(1)
    except KeyboardInterrupt:
        print_error("\nUpload cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        logger.exception("Unexpected error occurred")
        sys.exit(1)


if __name__ == '__main__':
    main()
