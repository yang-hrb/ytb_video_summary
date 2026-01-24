#!/usr/bin/env python3
"""Upload markdown files to GitHub using repository configuration."""

import argparse
import json
import logging
from pathlib import Path

from src.upload_to_github import find_markdown_files, upload_files


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload markdown files to GitHub")
    parser.add_argument("--local-dir", required=True, help="Local directory with .md files")
    parser.add_argument(
        "--remote-folder",
        default="reports",
        help="Remote folder in GitHub repository",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip files that already exist in the repo",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    local_dir = Path(args.local_dir).expanduser().resolve()

    files = find_markdown_files(local_dir)
    if not files:
        logger.info("No markdown files found in %s", local_dir)
        print(json.dumps({"total": 0, "success": 0, "failed": 0, "skipped": 0}))
        return

    results = upload_files(
        files,
        remote_folder=args.remote_folder,
        skip_existing=args.skip_existing,
    )

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
