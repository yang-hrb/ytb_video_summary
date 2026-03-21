"""CLI命令处理模块

提供统一的命令处理接口，将参数解析与业务逻辑分离。
"""

import sys
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from config import config
from src.cli.display import (
    display_stats,
    display_failed_runs,
    display_resumable_runs,
    display_watch_channels,
    display_daily_summary_url,
)

logger = logging.getLogger(__name__)


class CommandHandler:
    """CLI命令处理器"""

    def __init__(self, args):
        self.args = args

    def execute(self) -> None:
        try:
            config.validate()
        except ValueError as e:
            logger.error(str(e))
            logger.error("Please ensure OPENROUTER_API_KEY is set in .env file")
            sys.exit(1)

        try:
            if self.args.status:
                self._handle_status()
            elif self.args.list_failed:
                self._handle_list_failed()
            elif self.args.list_resumable:
                self._handle_list_resumable()
            elif self.args.resume_only:
                self._handle_resume_only()
            elif self.args.import_watchlist:
                self._handle_import_watchlist()
            elif self.args.list_watch_channels:
                self._handle_list_watch_channels()
            elif self.args.watch_run_once:
                self._handle_watch_run_once()
            elif self.args.watch_daemon:
                self._handle_watch_daemon()
            elif self.args.daily_summary is not None:
                self._handle_daily_summary()
            elif self.args.batch:
                self._handle_batch()
            elif self.args.local:
                self._handle_local()
            elif self.args.apple_podcast_single:
                self._handle_apple_podcast_single()
            elif self.args.apple_podcast_list:
                self._handle_apple_podcast_list()
            elif self.args.list:
                self._handle_playlist()
            elif self.args.video:
                self._handle_video()
            elif self.args.url:
                self._handle_default_url()
            else:
                self._show_usage()

            self._post_process()

        except KeyboardInterrupt:
            logger.error("User interrupted")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Program exited abnormally: {e}")
            sys.exit(1)

    def _handle_status(self) -> None:
        from src.run_tracker import get_tracker
        tracker = get_tracker()
        stats = tracker.get_stats()
        display_stats(stats)

    def _handle_list_failed(self) -> None:
        from src.run_tracker import get_tracker
        tracker = get_tracker()
        runs = tracker.get_failed_runs()
        display_failed_runs(runs)

    def _handle_list_resumable(self) -> None:
        from src.run_tracker import get_tracker, RunTracker
        tracker = get_tracker()
        runs = tracker.get_resumable_runs()
        display_resumable_runs(runs, RunTracker.RESUMABLE_STATUS_MAP)

    def _handle_resume_only(self) -> None:
        from src.main import process_resume_only
        logger.info("Resume-only mode")
        process_resume_only(summary_style=self.args.style, upload=self.args.upload)

    def _handle_import_watchlist(self) -> None:
        from src.channel_watcher import ChannelWatcher
        w = ChannelWatcher(
            cookies_file=self.args.cookies,
            cookies_from_browser=self.args.cookies_from_browser,
            browser=self.args.browser
        )
        w.import_watchlist(Path(self.args.import_watchlist))

    def _handle_list_watch_channels(self) -> None:
        from src.channel_watcher import ChannelWatcher
        w = ChannelWatcher()
        channels = w.list_watch_channels()
        display_watch_channels(channels)

    def _handle_watch_run_once(self) -> None:
        from src.channel_watcher import ChannelWatcher
        logger.info("Executing single watch scan...")
        w = ChannelWatcher(
            cookies_file=self.args.cookies,
            cookies_from_browser=self.args.cookies_from_browser,
            browser=self.args.browser
        )
        processed = w.execute_scan(upload=self.args.upload)
        logger.info(f"Scan complete. Processed {processed} videos.")

    def _handle_watch_daemon(self) -> None:
        from src.channel_watcher import ChannelWatcher
        logger.info("Starting watcher daemon (pressing Ctrl+C to stop)...")
        w = ChannelWatcher(
            cookies_file=self.args.cookies,
            cookies_from_browser=self.args.cookies_from_browser,
            browser=self.args.browser
        )
        interval = 3600
        if self.args.watch_time:
            try:
                interval = int(self.args.watch_time)
            except ValueError:
                logger.warning("Could not parse watch_time as int seconds, using 3600s.")
        try:
            while True:
                w.execute_scan(upload=self.args.upload)
                logger.info(f"Sleeping for {interval}s")
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Daemon stopped.")

    def _handle_daily_summary(self) -> None:
        from src.daily_summary import generate_daily_summary
        date_str = None if self.args.daily_summary == 'today' else self.args.daily_summary
        url = generate_daily_summary(target_date=date_str, upload=self.args.upload)
        display_daily_summary_url(url)

    def _handle_batch(self) -> None:
        from src.main import _process_batch_file
        batch_file = Path(self.args.batch)
        if not batch_file.exists():
            logger.error(f"Batch file does not exist: {batch_file}")
            sys.exit(1)

        logger.info("Batch processing mode")
        logger.info(f"Batch file: {batch_file.absolute()}")

        _process_batch_file(
            batch_file,
            cookies_file=self.args.cookies,
            cookies_from_browser=self.args.cookies_from_browser,
            browser=self.args.browser,
            keep_audio=self.args.keep_audio,
            summary_style=self.args.style,
            upload=self.args.upload
        )

    def _handle_local(self) -> None:
        from src.main import process_local_folder
        folder_path = Path(self.args.local)
        if not folder_path.exists():
            logger.error(f"Folder does not exist: {folder_path}")
            sys.exit(1)
        if not folder_path.is_dir():
            logger.error(f"Path is not a folder: {folder_path}")
            sys.exit(1)

        logger.info("Local MP3 folder mode")
        logger.info(f"Folder path: {folder_path.absolute()}")

        process_local_folder(
            folder_path,
            summary_style=self.args.style,
            upload_to_github_repo=self.args.upload
        )

    def _handle_apple_podcast_single(self) -> None:
        from src.main import process_apple_podcast
        logger.info("Apple Podcasts single episode mode")
        process_apple_podcast(
            self.args.apple_podcast_single,
            episode_index=0,
            summary_style=self.args.style,
            upload_to_github_repo=self.args.upload
        )

    def _handle_apple_podcast_list(self) -> None:
        from src.main import process_apple_podcast_show
        logger.info("Apple Podcasts show mode")
        process_apple_podcast_show(
            self.args.apple_podcast_list,
            summary_style=self.args.style,
            upload_to_github_repo=self.args.upload
        )

    def _handle_playlist(self) -> None:
        from src.main import process_playlist
        logger.info("YouTube playlist mode")
        process_playlist(
            self.args.list,
            cookies_file=self.args.cookies,
            cookies_from_browser=self.args.cookies_from_browser,
            browser=self.args.browser,
            keep_audio=self.args.keep_audio,
            summary_style=self.args.style,
            upload_to_github_repo=self.args.upload
        )

    def _handle_video(self) -> None:
        from src.main import process_video
        logger.info("YouTube single video mode")
        process_video(
            self.args.video,
            cookies_file=self.args.cookies,
            cookies_from_browser=self.args.cookies_from_browser,
            browser=self.args.browser,
            keep_audio=self.args.keep_audio,
            summary_style=self.args.style,
            upload_to_github_repo=self.args.upload
        )

    def _handle_default_url(self) -> None:
        from src.main import process_video, process_playlist, process_apple_podcast
        from src.utils import is_playlist_url, is_apple_podcasts_url

        if is_apple_podcasts_url(self.args.url):
            logger.info("Detected Apple Podcasts URL (single episode)")
            process_apple_podcast(
                self.args.url,
                episode_index=0,
                summary_style=self.args.style,
                upload_to_github_repo=self.args.upload
            )
        elif is_playlist_url(self.args.url):
            logger.info("Detected YouTube playlist")
            process_playlist(
                self.args.url,
                cookies_file=self.args.cookies,
                cookies_from_browser=self.args.cookies_from_browser,
                browser=self.args.browser,
                keep_audio=self.args.keep_audio,
                summary_style=self.args.style,
                upload_to_github_repo=self.args.upload
            )
        else:
            logger.info("Detected YouTube single video")
            process_video(
                self.args.url,
                cookies_file=self.args.cookies,
                cookies_from_browser=self.args.cookies_from_browser,
                browser=self.args.browser,
                keep_audio=self.args.keep_audio,
                summary_style=self.args.style,
                upload_to_github_repo=self.args.upload
            )

    def _show_usage(self) -> None:
        logger.error("Please provide input parameters")
        logger.info("Usage:")
        logger.info("  python src/main.py -video <YouTube video URL>")
        logger.info("  python src/main.py -list <YouTube playlist URL>")
        logger.info("  python src/main.py --apple-podcast-single <Apple Podcasts URL>")
        logger.info("  python src/main.py --apple-podcast-list <Apple Podcasts URL>")
        logger.info("  python src/main.py -local <MP3 folder path>")
        logger.info("  python src/main.py --batch <input file>")
        logger.info("Or use default mode:")
        logger.info("  python src/main.py <URL>")
        logger.info("Use --help for detailed help")
        sys.exit(1)

    def _post_process(self) -> None:
        if self.args.upload and (config.GITHUB_TOKEN and config.GITHUB_REPO):
            try:
                from src.daily_summary import generate_daily_summary
                logger.info("")
                logger.info("=" * 60)
                logger.info("[Final] Generating and uploading daily digest...")
                generate_daily_summary(upload=True)
            except Exception as e:
                logger.warning(f"Failed to generate daily digest: {e}")

        if self.args.upload and (config.GITHUB_TOKEN and config.GITHUB_REPO):
            logger.info("")
            logger.info("=" * 60)
            logger.info("[Final] Uploading logs and database to GitHub...")
            try:
                from src.logger import get_current_log_file
                from src.github_handler import upload_logs_to_github
                current_log = get_current_log_file()
                log_results = upload_logs_to_github(current_log)
                if log_results['db_url']:
                    logger.info(f"  Database: {log_results['db_url']}")
                if log_results['log_files']:
                    logger.info(f"  Uploaded {len(log_results['log_files'])} log file(s)")
                logger.info("Logs uploaded successfully!")
            except Exception as e:
                logger.warning(f"Failed to upload logs: {e}")
