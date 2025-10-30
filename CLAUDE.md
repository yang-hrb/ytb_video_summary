# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Video Transcription & Summarization Tool - A Python CLI application that downloads YouTube videos (including membership content), transcribes audio to text using OpenAI Whisper, and generates AI-powered summaries using OpenRouter API.

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

# Basic usage
python src/main.py "https://youtube.com/watch?v=xxxxx"

# With options
python src/main.py "URL" --style brief
python src/main.py "URL" --keep-audio
python src/main.py "URL" --cookies cookies.txt
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
- Orchestrates the entire pipeline
- Handles user interaction with colorama-formatted output
- Manages configuration validation before processing

**`src/youtube_handler.py`**
- `YouTubeHandler` class wraps yt-dlp functionality
- `get_video_info()` - Extracts metadata without downloading
- `download_subtitles()` - Attempts to fetch existing subtitles (Chinese/English)
- `download_audio()` - Downloads best audio quality when subtitles unavailable
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
- `create_report_filename()` - Generates timestamped filenames: `YYYYMMDD_HHMM_title.md`
- `extract_video_id()` - Parses various YouTube URL formats

### Directory Structure

```
output/
├── transcripts/    # [video_id]_transcript.srt - SRT files with timestamps
├── summaries/      # [video_id]_summary.md - Summaries indexed by video ID
└── reports/        # [timestamp]_[title].md - User-friendly timestamped reports
temp/               # Temporary audio files (auto-cleaned unless --keep-audio)
```

### Configuration System

All settings are managed through `.env` file and accessed via `config.config` singleton:

- **OPENROUTER_API_KEY** - Required for AI summarization
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
from src.main import process_video

result = process_video(
    url="https://youtube.com/watch?v=xxxxx",
    keep_audio=False,
    summary_style="detailed"
)
# Returns dict with: video_id, video_info, transcript, transcript_file, summary_file, report_file
```

### Membership Video Support
Uses cookies for authentication:
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

## External Dependencies

- **FFmpeg** - Must be installed system-wide for audio processing (brew install ffmpeg on Mac)
- **yt-dlp** - YouTube downloader (handles both public and membership content)
- **OpenAI Whisper** - Local speech-to-text transcription
- **OpenRouter API** - Cloud-based AI summarization using deepseek/deepseek-r1 model

## Testing Notes

Tests are organized in `tests/` directory with one file per module. When adding new features, maintain this structure and ensure tests cover both success and error paths.
