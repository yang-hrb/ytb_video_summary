#!/usr/bin/env python3
"""
YouTube 视频转录与总结工具 - 主程序
"""

import argparse
import sys
from pathlib import Path
import logging
from typing import Optional

from colorama import init, Fore, Style

# Ensure project root is on sys.path so imports work whether the user runs
# `python src/main.py` or `python -m src.main` from the repository root.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import config
from src.youtube_handler import process_youtube_video, get_playlist_videos
from src.transcriber import transcribe_video_audio, read_subtitle_file, Transcriber
from src.summarizer import summarize_transcript
from src.utils import clean_temp_files, get_file_size_mb, is_playlist_url, extract_playlist_id, sanitize_filename
from src.notion_handler import save_to_notion

# 初始化 colorama
init(autoreset=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('youtube_summarizer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def print_banner():
    """打印程序横幅"""
    banner = f"""
{Fore.CYAN}╔═══════════════════════════════════════════════════════════╗
║   音频/视频转录与总结工具 v2.0                             ║
║   Audio/Video Transcript & Summarizer                     ║
║   支持: YouTube 视频/播放列表 + 本地 MP3                    ║
╚═══════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)


def print_step(step: str, description: str):
    """打印步骤信息"""
    print(f"\n{Fore.GREEN}[{step}]{Style.RESET_ALL} {description}")


def print_error(message: str):
    """打印错误信息"""
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {message}")


def print_success(message: str):
    """打印成功信息"""
    print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {message}")


def process_video(
    url: str,
    cookies_file: Optional[str] = None,
    keep_audio: bool = False,
    summary_style: str = "detailed"
) -> dict:
    """
    处理单个视频的完整流程

    Args:
        url: YouTube 视频 URL
        cookies_file: cookies.txt 文件路径
        keep_audio: 是否保留音频文件
        summary_style: 总结风格 (brief/detailed)

    Returns:
        包含处理结果的字典
    """
    try:
        # Step 1: 下载视频信息和字幕/音频
        print_step("1/4", "正在获取视频信息...")
        result = process_youtube_video(url, cookies_file)

        video_info = result['info']
        video_id = result['video_id']

        print(f"  标题: {video_info['title']}")
        print(f"  时长: {video_info['duration']}s")
        print(f"  作者: {video_info['uploader']}")

        # Step 2: 获取转录文本
        transcript = None

        if result['needs_transcription']:
            print_step("2/4", "正在使用 Whisper 转录音频...")
            audio_path = result['audio_path']
            print(f"  音频文件: {audio_path}")
            print(f"  文件大小: {get_file_size_mb(audio_path):.2f} MB")

            transcript = transcribe_video_audio(audio_path, video_id, save_srt=True)

            # 清理音频文件
            if not keep_audio and not config.KEEP_AUDIO:
                print("  正在清理音频文件...")
                audio_path.unlink()
        else:
            print_step("2/4", "正在读取字幕文件...")
            subtitle_path = result['subtitle_path']
            print(f"  字幕文件: {subtitle_path}")
            transcript = read_subtitle_file(subtitle_path)

        print(f"  转录文本长度: {len(transcript)} 字符")

        # Step 3: 生成 AI 总结
        print_step("3/4", "正在生成 AI 总结...")
        print(f"  使用风格: {summary_style}")

        summary_result = summarize_transcript(
            transcript,
            video_id,
            video_info,
            style=summary_style,
            video_url=url
        )

        # Step 4: 输出结果
        print_step("4/4", "处理完成!")

        transcript_file = config.TRANSCRIPT_DIR / f"{video_id}_transcript.srt"
        summary_file = summary_result['summary_path']
        report_file = summary_result['report_path']
        notion_url = summary_result.get('notion_url')

        print(f"\n{Fore.CYAN}输出文件:{Style.RESET_ALL}")
        print(f"  转录: {transcript_file}")
        print(f"  总结: {summary_file}")
        if report_file:
            print(f"  报告: {report_file}")
        if notion_url:
            print(f"\n{Fore.CYAN}Notion 页面:{Style.RESET_ALL}")
            print(f"  {notion_url}")

        print_success("视频处理完成!")

        return {
            'video_id': video_id,
            'video_info': video_info,
            'transcript': transcript,
            'transcript_file': transcript_file,
            'summary_file': summary_file,
            'report_file': report_file,
            'notion_url': notion_url
        }

    except Exception as e:
        print_error(f"处理失败: {e}")
        logger.exception("Error processing video")
        raise


def process_local_mp3(
    mp3_path: Path,
    summary_style: str = "detailed"
) -> dict:
    """
    处理本地 MP3 文件的完整流程

    Args:
        mp3_path: MP3 文件路径
        summary_style: 总结风格 (brief/detailed)

    Returns:
        包含处理结果的字典
    """
    try:
        file_name = mp3_path.stem  # 不含扩展名的文件名

        print(f"  文件: {mp3_path.name}")
        print(f"  大小: {get_file_size_mb(mp3_path):.2f} MB")

        # Step 1: 转录音频
        print_step("1/3", "正在使用 Whisper 转录音频...")

        transcriber = Transcriber()
        result = transcriber.transcribe_audio(mp3_path)
        transcript = transcriber.get_transcript_text(result)

        # 保存 SRT 文件
        srt_path = config.TRANSCRIPT_DIR / f"{file_name}_transcript.srt"
        transcriber.save_as_srt(result, srt_path)

        print(f"  转录文本长度: {len(transcript)} 字符")

        # Step 2: 生成 AI 总结
        print_step("2/3", "正在生成 AI 总结...")
        print(f"  使用风格: {summary_style}")

        # 为本地文件创建虚拟的 video_info
        video_info = {
            'title': file_name,
            'uploader': 'Local Audio',
            'duration': int(result.get('segments', [{}])[-1].get('end', 0)) if result.get('segments') else 0
        }

        summary_result = summarize_transcript(
            transcript,
            file_name,
            video_info,
            style=summary_style,
            video_url=None
        )

        # Step 3: 输出结果
        print_step("3/3", "处理完成!")

        summary_file = summary_result['summary_path']
        report_file = summary_result['report_path']
        notion_url = summary_result.get('notion_url')

        print(f"\n{Fore.CYAN}输出文件:{Style.RESET_ALL}")
        print(f"  转录: {srt_path}")
        print(f"  总结: {summary_file}")
        if report_file:
            print(f"  报告: {report_file}")
        if notion_url:
            print(f"\n{Fore.CYAN}Notion 页面:{Style.RESET_ALL}")
            print(f"  {notion_url}")

        print_success("音频处理完成!")

        return {
            'file_name': file_name,
            'file_path': mp3_path,
            'transcript': transcript,
            'transcript_file': srt_path,
            'summary_file': summary_file,
            'report_file': report_file,
            'notion_url': notion_url
        }

    except Exception as e:
        print_error(f"处理失败: {e}")
        logger.exception("Error processing local MP3")
        raise


def process_local_folder(
    folder_path: Path,
    summary_style: str = "detailed"
) -> list:
    """
    处理本地文件夹中的所有 MP3 文件

    Args:
        folder_path: 文件夹路径
        summary_style: 总结风格 (brief/detailed)

    Returns:
        包含所有文件处理结果的列表
    """
    try:
        # 查找所有 MP3 文件
        print_step("0", "正在扫描 MP3 文件...")
        mp3_files = list(folder_path.glob("*.mp3"))

        if not mp3_files:
            print_error(f"文件夹中没有找到 MP3 文件: {folder_path}")
            return []

        print(f"  找到 {len(mp3_files)} 个 MP3 文件")
        print(f"\n{Fore.YELLOW}开始处理 MP3 文件...{Style.RESET_ALL}\n")

        # 处理每个文件
        results = []
        failed_files = []

        for idx, mp3_file in enumerate(mp3_files, 1):
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}处理文件 [{idx}/{len(mp3_files)}]{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

            try:
                result = process_local_mp3(
                    mp3_file,
                    summary_style=summary_style
                )
                results.append(result)
            except Exception as e:
                print_error(f"文件 {idx} 处理失败: {e}")
                logger.exception(f"Failed to process file {idx}: {mp3_file}")
                failed_files.append((idx, mp3_file.name, str(e)))
                # 继续处理下一个文件
                continue

        # 输出总结
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}文件夹处理完成{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        print(f"{Fore.GREEN}成功处理: {len(results)}/{len(mp3_files)} 个文件{Style.RESET_ALL}")

        if failed_files:
            print(f"\n{Fore.YELLOW}失败的文件:{Style.RESET_ALL}")
            for idx, filename, error in failed_files:
                print(f"  [{idx}] {filename}")
                print(f"      错误: {error}")

        return results

    except Exception as e:
        print_error(f"文件夹处理失败: {e}")
        logger.exception("Error processing local folder")
        raise


def process_playlist(
    playlist_url: str,
    cookies_file: Optional[str] = None,
    keep_audio: bool = False,
    summary_style: str = "detailed"
) -> list:
    """
    处理播放列表中的所有视频

    Args:
        playlist_url: YouTube 播放列表 URL
        cookies_file: cookies.txt 文件路径
        keep_audio: 是否保留音频文件
        summary_style: 总结风格 (brief/detailed)

    Returns:
        包含所有视频处理结果的列表
    """
    try:
        # 获取播放列表中的所有视频
        print_step("0", "正在获取播放列表信息...")
        playlist_id = extract_playlist_id(playlist_url)
        print(f"  播放列表 ID: {playlist_id}")

        video_urls = get_playlist_videos(playlist_url, cookies_file)

        if not video_urls:
            print_error("播放列表中没有找到视频")
            return []

        print(f"  找到 {len(video_urls)} 个视频")
        print(f"\n{Fore.YELLOW}开始处理播放列表中的视频...{Style.RESET_ALL}\n")

        # 处理每个视频
        results = []
        failed_videos = []

        for idx, video_url in enumerate(video_urls, 1):
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}处理视频 [{idx}/{len(video_urls)}]{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

            try:
                result = process_video(
                    video_url,
                    cookies_file=cookies_file,
                    keep_audio=keep_audio,
                    summary_style=summary_style
                )
                results.append(result)
            except Exception as e:
                print_error(f"视频 {idx} 处理失败: {e}")
                logger.exception(f"Failed to process video {idx}: {video_url}")
                failed_videos.append((idx, video_url, str(e)))
                # 继续处理下一个视频
                continue

        # 输出总结
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}播放列表处理完成{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        print(f"{Fore.GREEN}成功处理: {len(results)}/{len(video_urls)} 个视频{Style.RESET_ALL}")

        if failed_videos:
            print(f"\n{Fore.YELLOW}失败的视频:{Style.RESET_ALL}")
            for idx, url, error in failed_videos:
                print(f"  [{idx}] {url}")
                print(f"      错误: {error}")

        return results

    except Exception as e:
        print_error(f"播放列表处理失败: {e}")
        logger.exception("Error processing playlist")
        raise


def main():
    """主函数 - 命令行入口"""
    parser = argparse.ArgumentParser(
        description='音频/视频转录与总结工具 - 支持 YouTube 和本地 MP3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理单个 YouTube 视频（默认）
  python src/main.py "https://youtube.com/watch?v=xxxxx"
  python src/main.py -video "https://youtube.com/watch?v=xxxxx" --style brief

  # 处理 YouTube 播放列表
  python src/main.py -list "https://youtube.com/playlist?list=xxxxx"
  python src/main.py -list "https://youtube.com/watch?v=xxxxx&list=xxxxx"

  # 处理本地 MP3 文件夹
  python src/main.py -local /path/to/mp3/folder
  python src/main.py -local ./audio_files --style detailed
        """
    )

    # 创建互斥组：-video, -list, -local 三选一
    input_group = parser.add_mutually_exclusive_group()

    input_group.add_argument(
        '-video',
        type=str,
        metavar='URL',
        help='YouTube 视频 URL'
    )

    input_group.add_argument(
        '-list',
        type=str,
        metavar='URL',
        help='YouTube 播放列表 URL'
    )

    input_group.add_argument(
        '-local',
        type=str,
        metavar='PATH',
        help='本地 MP3 文件夹路径'
    )

    # 保留位置参数以支持旧的使用方式（向后兼容）
    parser.add_argument(
        'url',
        nargs='?',
        help='YouTube 视频或播放列表 URL（默认模式）'
    )

    parser.add_argument(
        '--cookies',
        type=str,
        help='cookies.txt 文件路径（用于会员视频）'
    )

    parser.add_argument(
        '--keep-audio',
        action='store_true',
        help='保留下载的音频文件（仅用于 YouTube）'
    )

    parser.add_argument(
        '--style',
        choices=['brief', 'detailed'],
        default='detailed',
        help='总结风格: brief (简短) 或 detailed (详细)'
    )

    args = parser.parse_args()

    # 打印横幅
    print_banner()

    # 验证配置
    try:
        config.validate()
    except ValueError as e:
        print_error(str(e))
        print("\n请确保 .env 文件中设置了 OPENROUTER_API_KEY")
        sys.exit(1)

    # 确定处理模式
    try:
        if args.local:
            # 本地 MP3 文件夹模式
            folder_path = Path(args.local)
            if not folder_path.exists():
                print_error(f"文件夹不存在: {folder_path}")
                sys.exit(1)
            if not folder_path.is_dir():
                print_error(f"路径不是文件夹: {folder_path}")
                sys.exit(1)

            print(f"{Fore.YELLOW}本地 MP3 文件夹模式{Style.RESET_ALL}\n")
            print(f"文件夹路径: {folder_path.absolute()}\n")

            results = process_local_folder(
                folder_path,
                summary_style=args.style
            )

        elif args.list:
            # YouTube 播放列表模式
            print(f"{Fore.YELLOW}YouTube 播放列表模式{Style.RESET_ALL}\n")
            results = process_playlist(
                args.list,
                cookies_file=args.cookies,
                keep_audio=args.keep_audio,
                summary_style=args.style
            )

        elif args.video:
            # YouTube 单个视频模式
            print(f"{Fore.YELLOW}YouTube 单个视频模式{Style.RESET_ALL}\n")
            result = process_video(
                args.video,
                cookies_file=args.cookies,
                keep_audio=args.keep_audio,
                summary_style=args.style
            )

        elif args.url:
            # 默认模式（向后兼容）- 自动检测 YouTube URL 类型
            if is_playlist_url(args.url):
                print(f"{Fore.YELLOW}检测到 YouTube 播放列表{Style.RESET_ALL}\n")
                results = process_playlist(
                    args.url,
                    cookies_file=args.cookies,
                    keep_audio=args.keep_audio,
                    summary_style=args.style
                )
            else:
                print(f"{Fore.YELLOW}检测到 YouTube 单个视频{Style.RESET_ALL}\n")
                result = process_video(
                    args.url,
                    cookies_file=args.cookies,
                    keep_audio=args.keep_audio,
                    summary_style=args.style
                )

        else:
            # 没有提供任何输入
            print_error("请提供输入参数")
            print("\n使用方式:")
            print("  python src/main.py -video <YouTube视频URL>")
            print("  python src/main.py -list <YouTube播放列表URL>")
            print("  python src/main.py -local <MP3文件夹路径>")
            print("\n或使用默认模式:")
            print("  python src/main.py <YouTube URL>")
            print("\n使用 --help 查看详细帮助")
            sys.exit(1)

        sys.exit(0)

    except KeyboardInterrupt:
        print_error("\n用户中断")
        sys.exit(1)
    except Exception as e:
        print_error(f"程序异常退出: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
