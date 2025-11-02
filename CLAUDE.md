# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Audio/Video Transcription & Summarization Tool - A Python CLI application that:
- Downloads YouTube videos (including membership content) and playlists
- Processes local MP3 files from folders
- Transcribes audio to text using OpenAI Whisper
- Generates AI-powered summaries using OpenRouter API
- Optionally syncs summaries to Notion for knowledge management

## Essential Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

### Running the Application

**Quick Start Scripts:**
```bash
# Simple mode - just paste URL, uses defaults
./quick-run.sh

# Full mode - with options for style, keep-audio, cookies
./run.sh
```

**Manual Execution:**
```bash
# Activate venv first
source venv/bin/activate

# Single YouTube video (default mode)
python src/main.py "https://youtube.com/watch?v=xxxxx"
python src/main.py -video "https://youtube.com/watch?v=xxxxx"

# YouTube playlist
python src/main.py -list "https://youtube.com/playlist?list=xxxxx"
python src/main.py -list "https://youtube.com/watch?v=xxxxx&list=xxxxx"

# Local MP3 folder
python src/main.py -local /path/to/mp3/folder
python src/main.py -local ./audio_files --style detailed

# With options
python src/main.py -video "URL" --style brief --keep-audio
python src/main.py -list "URL" --cookies cookies.txt
```

### Testing
```bash
# Run all tests
python -m unittest discover tests

# Run specific test module
python -m unittest tests.test_youtube
python -m unittest tests.test_transcriber
python -m unittest tests.test_summarizer
```

## Architecture Overview

### Core Processing Pipeline

The application follows a 4-step sequential pipeline (implemented in `src/main.py:process_video()`):

1. **Video Acquisition** (`youtube_handler.py`) - Downloads video metadata and attempts subtitle extraction. If subtitles unavailable, downloads audio for transcription.
2. **Transcription** (`transcriber.py`) - Either reads existing subtitles or uses Whisper to transcribe downloaded audio to text with timestamps.
3. **AI Summarization** (`summarizer.py`) - Sends transcript to OpenRouter API for intelligent summarization in specified style (brief/detailed).
4. **Output Generation** - Creates three output files: SRT transcript, summary by video ID, and timestamped report by title.

### Module Responsibilities

**`src/main.py`**
- CLI entry point with argument parsing
- Supports three input modes: `-video` (YouTube video), `-list` (YouTube playlist), `-local` (MP3 folder)
- Orchestrates the entire pipeline for videos, playlists, and local audio files
- `process_video()` - Processes a single YouTube video through the 4-step pipeline
- `process_playlist()` - Processes all videos in a YouTube playlist sequentially
- `process_local_mp3()` - Processes a single local MP3 file through the 3-step pipeline
- `process_local_folder()` - Batch processes all MP3 files in a folder
- Automatically detects URLs and routes to appropriate handler
- Handles user interaction with colorama-formatted output
- Manages configuration validation before processing

**`src/youtube_handler.py`**
- `YouTubeHandler` class wraps yt-dlp functionality
- `get_video_info()` - Extracts metadata without downloading
- `download_subtitles()` - Attempts to fetch existing subtitles (Chinese/English)
- `download_audio()` - Downloads best audio quality when subtitles unavailable
- `get_playlist_videos()` - Extracts all video URLs from a YouTube playlist
- `process_youtube_video()` - Convenience function that decides subtitle vs audio path

**`src/transcriber.py`**
- `Transcriber` class manages Whisper model lifecycle
- Lazy-loads Whisper model on first transcription (saves memory)
- `transcribe_audio()` - Converts audio to text with word-level timestamps
- `save_as_srt()` - Formats output as standard SRT subtitle file
- `read_subtitle_file()` - Parses existing SRT files to extract plain text

**`src/summarizer.py`**
- `Summarizer` class handles OpenRouter API communication
- Creates style-specific prompts (brief vs detailed) in Chinese
- `summarize()` - Sends transcript to deepseek/deepseek-r1 model
- `save_summary()` - Generates two outputs: video_id-based summary and timestamped report

**`config/settings.py`**
- `Config` singleton pattern for environment variables
- Auto-creates required directory structure on initialization
- `validate()` method ensures OPENROUTER_API_KEY is set before processing

**`src/utils.py`**
- Filename sanitization and timestamp formatting utilities
- `create_report_filename()` - Generates enhanced filenames: `YYYYMMDD_HHMM_[uploader]_[content-title].md`
- `extract_summary_title()` - Extracts a descriptive title from AI-generated summary content
- `extract_video_id()` - Parses various YouTube URL formats
- `is_playlist_url()` - Detects if a URL is a YouTube playlist
- `extract_playlist_id()` - Extracts playlist ID from YouTube URLs

**`src/notion_handler.py`**
- `NotionHandler` class handles Notion API communication
- `create_page()` - Creates a new page in Notion database with video summary
- `markdown_to_notion_blocks()` - Converts Markdown content to Notion block format
- `save_to_notion()` - Convenience function for saving to Notion
- Gracefully handles missing Notion configuration (falls back to local-only saving)

### Directory Structure

```
output/
├── transcripts/    # [video_id]_transcript.srt - SRT files with timestamps
├── summaries/      # [video_id]_summary.md - Summaries indexed by video ID
└── reports/        # [timestamp]_[uploader]_[content-title].md - Enhanced timestamped reports
temp/               # Temporary audio files (auto-cleaned unless --keep-audio)
```

**Report Filename Format:**
Reports are saved with an enhanced filename format:
- Format: `YYYYMMDD_HHMM_[uploader]_[content-title].md`
- `[uploader]`: First 10 characters of the channel name
- `[content-title]`: AI-extracted title from the summary content (up to 50 chars)
- Example: `20250101_1430_TechChannel_introduction-to-machine-learning.md`

### Configuration System

All settings are managed through `.env` file and accessed via `config.config` singleton:

**Required:**
- **OPENROUTER_API_KEY** - Required for AI summarization

**Optional:**
- **NOTION_API_KEY** - Notion Integration Token (for automatic Notion sync)
- **NOTION_DATABASE_ID** - Notion Database ID (where summaries will be saved)
- **WHISPER_MODEL** - Model size (tiny/base/small/medium/large) - defaults to 'base'
- **WHISPER_LANGUAGE** - Language code (zh/en/auto) - defaults to 'zh'
- **AUDIO_QUALITY** - Download quality in kbps (32/64/96/128)
- **KEEP_AUDIO** - Whether to preserve downloaded audio files

The Config class auto-creates all required directories (`output/`, `temp/`, subdirectories) on instantiation.

## Important Implementation Details

### Path Resolution
`src/main.py` adds project root to `sys.path` to support both:
- `python src/main.py` (direct script execution)
- `python -m src.main` (module execution from root)

### Python API Usage
The tool can be imported and used programmatically:
```python
from src.main import process_video, process_playlist, process_local_mp3, process_local_folder
from pathlib import Path

# Process single YouTube video
result = process_video(
    url="https://youtube.com/watch?v=xxxxx",
    keep_audio=False,
    summary_style="detailed"
)
# Returns dict with: video_id, video_info, transcript, transcript_file, summary_file, report_file, notion_url

# Process YouTube playlist
results = process_playlist(
    playlist_url="https://youtube.com/playlist?list=xxxxx",
    keep_audio=False,
    summary_style="detailed"
)
# Returns list of result dicts, one for each successfully processed video

# Process single local MP3 file
result = process_local_mp3(
    mp3_path=Path("/path/to/audio.mp3"),
    summary_style="detailed"
)
# Returns dict with: file_name, file_path, transcript, transcript_file, summary_file, report_file, notion_url

# Process folder of MP3 files
results = process_local_folder(
    folder_path=Path("/path/to/mp3/folder"),
    summary_style="detailed"
)
# Returns list of result dicts, one for each successfully processed MP3 file
```

### Playlist Support
The application can process entire YouTube playlists:
- Automatically detects playlist URLs (both `playlist?list=` and `watch?v=xxx&list=` formats)
- Extracts all video URLs from the playlist using yt-dlp
- Processes each video sequentially through the standard pipeline
- Continues processing remaining videos even if individual videos fail
- Provides progress tracking (e.g., "Processing video [3/10]")
- Shows summary of successful and failed videos at completion

**Error Handling for Playlists:**
- If a video fails (age-restricted, removed, private, etc.), the error is logged
- Processing continues with the next video in the playlist
- Final summary shows count of successful/failed videos with error details

### Local MP3 Support
The application can process local MP3 files from a folder:
- Automatically scans folder for all .mp3 files
- Transcribes each file using Whisper
- Generates AI summaries for each audio file
- Optionally uploads to Notion
- Continues processing even if individual files fail
- Provides progress tracking and error summary

**Local MP3 Processing Pipeline (3 steps):**
1. **Transcription** - Convert MP3 to text using Whisper
2. **AI Summarization** - Generate summary with OpenRouter API
3. **Output** - Save transcript (SRT), summary, report, and optionally to Notion

**Metadata for Local Files:**
- Title: MP3 filename (without extension)
- Uploader: "Local Audio"
- Duration: Extracted from audio transcription

### Membership Video Support
Uses cookies for authentication (works for both single videos and playlists):
1. Export browser cookies using "Get cookies.txt" extension
2. Pass cookies file: `--cookies cookies.txt`
3. **Security**: cookies.txt is in .gitignore - never commit credentials

### Whisper Model Selection
First run downloads the selected model (~150MB for base). Larger models provide better accuracy but require more memory and processing time. The 'base' model provides good balance for most videos.

### FFmpeg Auto-Detection
The application automatically detects FFmpeg installation in the following order:
1. `FFMPEG_LOCATION` environment variable in .env
2. System PATH (using `which ffmpeg`)
3. Common installation locations:
   - `/opt/homebrew/bin` (macOS Homebrew Apple Silicon)
   - `/usr/local/bin` (macOS Homebrew Intel / Linux)
   - `/usr/bin` (Linux)
   - `C:\ffmpeg\bin` (Windows)

If FFmpeg is not auto-detected, set `FFMPEG_LOCATION` in your .env file.

### Audio File Cleanup
Downloaded audio files are automatically deleted after transcription unless:
- `--keep-audio` flag is used, OR
- `KEEP_AUDIO=true` in .env file

### Error Handling
The application uses Python logging to both console and `youtube_summarizer.log`. When debugging issues, check this log file for detailed error traces.

### OpenRouter API Configuration
The summarizer requires specific HTTP headers for OpenRouter API:
- `HTTP-Referer` - Required by OpenRouter for request tracking
- `X-Title` - Optional but recommended for better analytics
- `Authorization` - Bearer token with your API key

If you encounter 401 Unauthorized errors, verify:
1. OPENROUTER_API_KEY is set correctly in .env file
2. API key format starts with "sk-or-v1-" or similar
3. The required headers are present in the API request

## Notion Integration (Optional)

The tool can automatically save video summaries to Notion for centralized knowledge management.

**Setup Instructions:**
See [doc/NOTION_SETUP.md](doc/NOTION_SETUP.md) for detailed setup guide.

**Quick Setup:**
1. Create a Notion Integration at https://www.notion.so/my-integrations
2. Create a database in Notion with "Name" (Title) property
3. Share the database with your integration
4. Add to `.env`:
   ```
   NOTION_API_KEY=secret_xxxxx
   NOTION_DATABASE_ID=xxxxx
   ```

**Features:**
- Automatically creates Notion pages for each video summary
- Includes video metadata (title, uploader, duration, URL)
- Converts Markdown summary to Notion blocks
- Gracefully falls back to local-only saving if Notion is not configured
- Non-blocking - processing continues even if Notion save fails

## External Dependencies

- **FFmpeg** - Must be installed system-wide for audio processing (brew install ffmpeg on Mac)
- **yt-dlp** - YouTube downloader (handles both public and membership content)
- **OpenAI Whisper** - Local speech-to-text transcription
- **OpenRouter API** - Cloud-based AI summarization using deepseek/deepseek-r1 model
- **Notion API** (Optional) - Cloud-based knowledge management integration

## Testing Notes

Tests are organized in `tests/` directory with one file per module. When adding new features, maintain this structure and ensure tests cover both success and error paths.
