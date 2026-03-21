"""统一控制台输出模块

提供一致的控制台输出接口，区分日志和用户界面输出。
"""

from colorama import Fore, Style
import logging

logger = logging.getLogger(__name__)


def console_print(message: str, style: str = None) -> None:
    if style:
        print(f"{style}{message}{Style.RESET_ALL}")
    else:
        print(message)


def display_banner() -> None:
    banner = f"""
{Fore.CYAN}╔═══════════════════════════════════════════════════════════╗
║   Audio/Video Transcript & Summarizer v2.1                ║
║   YouTube + Apple Podcasts + Local MP3                    ║
╚═══════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    console_print(banner)


def display_stats(stats: dict) -> None:
    console_print("\n📊 Processing Statistics")
    console_print("=" * 40)
    console_print(f"  Total runs: {stats['total']}")

    console_print("\nBy status:")
    for status, count in sorted(stats['by_status'].items()):
        console_print(f"  {status:<25} {count}")

    console_print("\nBy type:")
    for run_type, count in sorted(stats['by_type'].items()):
        console_print(f"  {run_type:<25} {count}")

    console_print()


def display_failed_runs(runs: list) -> None:
    if not runs:
        console_print("\nNo failed runs found.")
        return

    console_print(f"\n❌ Failed runs ({len(runs)})")
    console_print("=" * 60)
    for r in runs:
        console_print(f"  id={r['id']} | status={r['status']} | stage={r.get('stage', '?')}")
        console_print(f"    identifier : {r['identifier']}")
        console_print(f"    url/path   : {r['url_or_path']}")
        console_print(f"    error      : {r.get('error_message', '')[:120]}")
        console_print(f"    updated_at : {r['updated_at']}")
        console_print()


def display_resumable_runs(runs: list, status_map: dict) -> None:
    if not runs:
        console_print("\nNo resumable runs found.")
        return

    console_print(f"\n🔄 Resumable runs ({len(runs)})")
    console_print("=" * 60)
    for r in runs:
        resume_stage = status_map.get(r['status'], '?')
        console_print(f"  id={r['id']} | status={r['status']} → resume from: {resume_stage}")
        console_print(f"    identifier : {r['identifier']}")
        console_print(f"    updated_at : {r['updated_at']}")
        console_print()


def display_watch_channels(channels: list) -> None:
    console_print("\n📺 Watchlist Channels")
    console_print("=" * 60)
    for c in channels:
        console_print(f"ID: {c['channel_id']} | Active: {c['is_active']} | "
                     f"Last seen: {c['last_seen_upload_date']} | "
                     f"Total processed: {c['videos_processed_total']}")


def display_daily_summary_url(url: str) -> None:
    console_print(f"Daily summary generated: {url}")
