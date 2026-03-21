# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Audio/Video Transcription & Summarization Tool - A Python CLI application that:
- Downloads YouTube videos (including membership content) and playlists
- Downloads and processes Apple Podcasts episodes and shows
- Processes local MP3 files from folders
- Transcribes audio to text using OpenAI Whisper
- Generates AI-powered summaries using OpenRouter with a model waterfall
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

# Apple Podcasts single episode (latest)
python src/main.py --apple-podcast-single "https://podcasts.apple.com/us/podcast/podcast-name/id123456789"
python src/main.py "https://podcasts.apple.com/us/podcast/podcast-name/id123456789"  # Auto-detect

# Apple Podcasts show (all episodes)
python src/main.py --apple-podcast-list "https://podcasts.apple.com/us/podcast/podcast-name/id123456789"

# Local MP3 folder
python src/main.py -local /path/to/mp3/folder
python src/main.py -local ./audio_files --style detailed

# With options
python src/main.py -video "URL" --style brief --keep-audio
python src/main.py -list "URL" --cookies cookies.txt
python src/main.py --apple-podcast-single "URL" --style detailed
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
3. **AI Summarization** (`summarizer.py`) - Sends transcript to OpenRouter for intelligent summarization in specified style (brief/detailed) using a model waterfall (Priority 1 -> 2 -> 3 -> Fallback).
4. **Output Generation** - Creates three output files: SRT transcript, summary by video ID, and timestamped report by title.

### Module Responsibilities

**`src/main.py`**
- CLI entry point with argument parsing
- Supports five input modes: `-video` (YouTube video), `-list` (YouTube playlist), `--apple-podcast-single` (single podcast episode), `--apple-podcast-list` (all episodes from podcast show), `-local` (MP3 folder)
- Orchestrates the entire pipeline for videos, playlists, podcasts, and local audio files
- Automatically detects URLs and routes to appropriate handler (YouTube, Apple Podcasts, or local)
- Manages configuration validation before processing

**`src/transcriber.py`**
- `Transcriber` class manages Whisper model lifecycle
- Lazy-loads Whisper model on first transcription (saves memory)
- `transcribe_audio()` - Converts audio to text with word-level timestamps
- `save_as_srt()` - Formats output as standard SRT subtitle file

**`src/summarizer.py`**
- `Summarizer` class handles OpenRouter API communication
- Uses a waterfall approach: Priority 1 -> Priority 2 -> Priority 3 -> Fallback Model
- Creates style-specific prompts (brief vs detailed) in multiple languages
- `summarize()` - Sends transcript to OpenRouter for summarization
- `save_summary()` - Generates two outputs: video_id-based summary and timestamped report

**`config/settings.py`**
- `Config` singleton pattern for environment variables
- Auto-creates required directory structure on initialization
- `validate()` method ensures OPENROUTER_API_KEY is set before processing

**`src/run_tracker.py`**
- `RunTracker` class manages SQLite database for tracking processing runs
- Records type (youtube/local), URL/path, identifier, and status
- Stores error messages for failed runs

### Directory Structure

```
output/
├── transcripts/    # [video_id]_transcript.srt - SRT files with timestamps
├── summaries/      # [video_id]_summary.md - Summaries indexed by video ID
└── reports/        # [timestamp]_[uploader]_[content-title].md - Enhanced timestamped reports
temp/               # Temporary audio files (auto-cleaned unless --keep-audio)
logs/
├── run_track.db    # SQLite database tracking all processing runs
├── failures_[timestamp].txt  # Timestamped failure logs
└── youtube_summarizer_[timestamp].log  # Application logs
```

### Configuration System

All settings are managed through `.env` file and accessed via `config.config` singleton:

**Required:**
- **OPENROUTER_API_KEY** - API key for OpenRouter

**Optional Model Configuration:**
- **OPENROUTER_MODEL** - Main model name
- **MODEL_PRIORITY_1**, **MODEL_PRIORITY_2**, **MODEL_PRIORITY_3** - Waterfall model sequence
- **MODEL_FALLBACK** - Final fallback model used when priorities fail

## Notion Integration (Optional)

The tool can automatically save video summaries to Notion.

**Quick Setup:**
1. Create a Notion Integration
2. Add to `.env`:
   ```
   NOTION_API_KEY=secret_xxxxx
   NOTION_DATABASE_ID=xxxxx
   ```

## External Dependencies

- **FFmpeg** - Must be installed system-wide for audio processing
- **yt-dlp** - YouTube downloader
- **OpenAI Whisper** - Local speech-to-text transcription
- **OpenRouter API** - Cloud-based AI summarization
- **Notion API** (Optional) - Cloud-based knowledge management integration

## Testing Notes

Tests are organized in `tests/` directory with one file per module. Maintain this structure and ensure tests cover both success and error paths.
