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
from tqdm import tqdm

# Ensure project root is on sys.path so imports work whether the user runs
# `python src/main.py` or `python -m src.main` from the repository root.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import config
from src.youtube_handler import process_youtube_video
from src.transcriber import transcribe_video_audio, read_subtitle_file
from src.summarizer import summarize_transcript
from src.utils import clean_temp_files, get_file_size_mb

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
║   YouTube 视频转录与总结工具 v1.0                          ║
║   YouTube Transcript & Summarizer                         ║
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
        
        print(f"\n{Fore.CYAN}输出文件:{Style.RESET_ALL}")
        print(f"  转录: {transcript_file}")
        print(f"  总结: {summary_file}")
        if report_file:
            print(f"  报告: {report_file}")
        
        print_success("视频处理完成!")
        
        return {
            'video_id': video_id,
            'video_info': video_info,
            'transcript': transcript,
            'transcript_file': transcript_file,
            'summary_file': summary_file,
            'report_file': report_file
        }
        
    except Exception as e:
        print_error(f"处理失败: {e}")
        logger.exception("Error processing video")
        raise


def main():
    """主函数 - 命令行入口"""
    parser = argparse.ArgumentParser(
        description='YouTube 视频转录与总结工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python src/main.py "https://youtube.com/watch?v=xxxxx"
  python src/main.py "URL" --style brief
  python src/main.py "URL" --keep-audio
  python src/main.py "URL" --cookies cookies.txt
        """
    )
    
    parser.add_argument(
        'url',
        help='YouTube 视频 URL'
    )
    
    parser.add_argument(
        '--cookies',
        type=str,
        help='cookies.txt 文件路径（用于会员视频）'
    )
    
    parser.add_argument(
        '--keep-audio',
        action='store_true',
        help='保留下载的音频文件'
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
    
    # 处理视频
    try:
        result = process_video(
            args.url,
            cookies_file=args.cookies,
            keep_audio=args.keep_audio,
            summary_style=args.style
        )
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        print_error("\n用户中断")
        sys.exit(1)
    except Exception as e:
        print_error(f"程序异常退出: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
