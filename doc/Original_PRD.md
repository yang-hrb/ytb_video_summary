# PRD - YouTube Video Transcription & Summarization Tool

## 📋 Project Overview

**Project Name**: YouTube Transcript & Summarizer
**Version**: v2.0
**Goal**: Automatically transcribe YouTube videos (including membership content) to text and generate AI-powered summaries

### Core Features
1. Support for YouTube public and membership videos
2. Support for YouTube playlists
3. Support for local MP3 files
4. Automatic subtitle extraction or generation
5. AI-powered video content summarization
6. Save storage space (optional audio deletion)
7. Optional Notion integration for knowledge management

---

## 🎯 Feature Requirements

### 1. Video Download
- [x] Support YouTube URL input
- [x] Support YouTube playlist URLs
- [x] Automatic video metadata extraction (title, duration, etc.)
- [x] Support membership videos (via browser cookies)
- [x] Download audio stream (64kbps MP3, space-efficient)

### 2. Local Audio Processing
- [x] Support local MP3 file processing
- [x] Support batch processing of MP3 folders
- [x] Transcribe local audio files
- [x] Generate summaries for local audio

### 3. Subtitle Generation
- [x] Priority extraction of YouTube native subtitles (if available)
- [x] Generate subtitles using Whisper (when no subtitles exist)
- [x] Support multiple languages (Chinese, English, etc.)
- [x] Output timestamped subtitle files (SRT/VTT)

### 4. AI Summarization
- [x] Use OpenRouter free models for summary generation
- [x] Support multiple summary styles (brief/detailed)
- [x] Extract key points
- [x] Generate timeline summary

### 5. Storage Optimization
- [x] Configurable audio quality (32/64/128 kbps)
- [x] Auto-delete audio after transcription (optional)
- [x] Save text results only

### 6. Notion Integration
- [x] Save summaries to Notion database
- [x] Automatic page creation with metadata
- [x] Convert Markdown to Notion blocks
- [x] Optional feature with graceful fallback

---

## 🛠 Technology Stack

### Core Technologies
| Technology | Purpose | Version Requirement |
|------------|---------|-------------------|
| **Python** | Main development language | 3.9+ |
| **yt-dlp** | YouTube video download | Latest |
| **OpenAI Whisper** | Speech-to-text | Latest |
| **OpenRouter API** | AI text summarization | - |
| **FFmpeg** | Audio processing | 4.0+ |
| **Notion API** | Knowledge management | - |

### Recommended Models
- **Whisper**: `base` model (recommended for M2 Mac)
- **Summarization**: DeepSeek R1 / Gemini 2.5 Flash (free)

### Development Environment
- **Hardware**: Mac Mini M2 (or equivalent)
- **OS**: macOS / Linux / Windows
- **Browser**: Chrome / Firefox / Edge (for cookies export)

---

## 📁 Project Structure

```
youtube-summarizer/
├── README.md                 # Project documentation
├── PRD.md                   # This document
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variable template
├── .gitignore              # Git ignore configuration
│
├── config/
│   ├── __init__.py
│   └── settings.py         # Configuration management
│
├── src/
│   ├── __init__.py
│   ├── main.py             # Main entry point
│   ├── youtube_handler.py  # YouTube download logic
│   ├── transcriber.py      # Whisper transcription logic
│   ├── summarizer.py       # AI summarization logic
│   ├── notion_handler.py   # Notion integration logic
│   └── utils.py            # Utility functions
│
├── output/                 # Output directory
│   ├── transcripts/        # Subtitle files
│   ├── summaries/          # Summary files
│   └── reports/            # Report files
│
├── temp/                   # Temporary files (audio)
│   └── .gitkeep
│
└── tests/                  # Unit tests
    ├── __init__.py
    ├── test_youtube.py
    ├── test_transcriber.py
    └── test_summarizer.py
```

---

## ⚙️ Configuration Guide

### 1. Environment Variables (`.env`)

```bash
# OpenRouter API
OPENROUTER_API_KEY=your_api_key_here

# Whisper Configuration
WHISPER_MODEL=base  # tiny/base/small/medium/large
WHISPER_LANGUAGE=zh  # zh/en/auto

# Audio Configuration
AUDIO_QUALITY=64  # 32/64/96/128 kbps
AUDIO_FORMAT=mp3  # mp3/opus
KEEP_AUDIO=false  # true/false

# Browser Configuration (for membership videos)
BROWSER_TYPE=chrome  # chrome/firefox/edge/safari
USE_COOKIES_FILE=false  # true to use cookies.txt

# Notion Configuration (optional)
NOTION_API_KEY=your_notion_integration_token
NOTION_DATABASE_ID=your_notion_database_id

# Output Configuration
OUTPUT_DIR=output
TEMP_DIR=temp
```

### 2. Configuration File (`config/settings.py`)

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
    NOTION_API_KEY = os.getenv('NOTION_API_KEY', '')
    NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID', '')

    # Whisper
    WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'base')
    WHISPER_LANGUAGE = os.getenv('WHISPER_LANGUAGE', 'zh')

    # Audio
    AUDIO_QUALITY = os.getenv('AUDIO_QUALITY', '64')
    AUDIO_FORMAT = os.getenv('AUDIO_FORMAT', 'mp3')
    KEEP_AUDIO = os.getenv('KEEP_AUDIO', 'false').lower() == 'true'

    # Browser
    BROWSER_TYPE = os.getenv('BROWSER_TYPE', 'chrome')
    USE_COOKIES_FILE = os.getenv('USE_COOKIES_FILE', 'false').lower() == 'true'

    # Paths
    BASE_DIR = Path(__file__).parent.parent
    OUTPUT_DIR = BASE_DIR / os.getenv('OUTPUT_DIR', 'output')
    TEMP_DIR = BASE_DIR / os.getenv('TEMP_DIR', 'temp')
    TRANSCRIPT_DIR = OUTPUT_DIR / 'transcripts'
    SUMMARY_DIR = OUTPUT_DIR / 'summaries'
    REPORT_DIR = OUTPUT_DIR / 'reports'

    # Auto-create directories
    for dir_path in [OUTPUT_DIR, TEMP_DIR, TRANSCRIPT_DIR, SUMMARY_DIR, REPORT_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)

config = Config()
```

### 3. Dependencies (`requirements.txt`)

```txt
# Core
yt-dlp>=2024.10.0
openai-whisper>=20231117
python-dotenv>=1.0.0

# API
requests>=2.31.0

# Audio Processing
ffmpeg-python>=0.2.0

# Utilities
colorama>=0.4.6

# Optional: Faster Whisper
# faster-whisper>=0.10.0
```

---

## 📝 Implementation Steps

### Phase 1: Environment Setup (Day 1)

**1.1 Install System Dependencies**
```bash
# Mac
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org
```

**1.2 Create Python Environment**
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

**1.3 Configure Environment Variables**
```bash
cp .env.example .env
# Edit .env file and add API keys
```

### Phase 2: Core Feature Development (Day 2-3)

**2.1 YouTube Download Module**
- Implement `youtube_handler.py`
- Support public video download
- Support membership videos (cookies)
- Support playlist processing
- Audio quality control

**2.2 Whisper Transcription Module**
- Implement `transcriber.py`
- Detect native subtitles
- Whisper transcription (when no subtitles)
- Output SRT format

**2.3 AI Summarization Module**
- Implement `summarizer.py`
- Integrate OpenRouter API
- Optimize prompts
- Structured output

**2.4 Notion Integration Module**
- Implement `notion_handler.py`
- Create Notion pages
- Convert Markdown to Notion blocks
- Handle optional configuration

### Phase 3: Integration & Optimization (Day 4)

**3.1 Main Program Integration**
- Implement `main.py`
- Command-line argument parsing
- Error handling
- Progress display

**3.2 Storage Optimization**
- Temporary file cleanup
- Auto audio deletion
- Output directory management

### Phase 4: Testing & Documentation (Day 5)

**4.1 Unit Testing**
- Test module functionality
- Handle edge cases

**4.2 Documentation**
- README usage guide
- Example code
- Troubleshooting guide

---

## ✅ Development Checklist

### Environment Preparation
- [x] Install Python 3.9+
- [x] Install FFmpeg
- [x] Create virtual environment
- [x] Install project dependencies
- [x] Configure .env file
- [x] Get OpenRouter API Key

### Module Development
- [x] Implement `config/settings.py`
- [x] Implement `src/youtube_handler.py`
  - [x] Public video download
  - [x] Membership video support (cookies)
  - [x] Playlist support
  - [x] Audio quality control
  - [x] Metadata extraction
- [x] Implement `src/transcriber.py`
  - [x] Detect native subtitles
  - [x] Whisper model loading
  - [x] Audio transcription
  - [x] SRT file generation
- [x] Implement `src/summarizer.py`
  - [x] OpenRouter API integration
  - [x] Prompt design
  - [x] Result parsing
  - [x] Error handling
- [x] Implement `src/notion_handler.py`
  - [x] Notion API integration
  - [x] Page creation
  - [x] Markdown to blocks conversion
  - [x] Optional configuration
- [x] Implement `src/utils.py`
  - [x] File management
  - [x] Logging
  - [x] Time formatting
- [x] Implement `src/main.py`
  - [x] Command-line arguments
  - [x] Process orchestration
  - [x] Progress display

### Feature Testing
- [x] Test public video download
- [x] Test membership video download
- [x] Test playlist processing
- [x] Test local MP3 processing
- [x] Test videos with subtitles (skip Whisper)
- [x] Test videos without subtitles (use Whisper)
- [x] Test Chinese videos
- [x] Test English videos
- [x] Test AI summary output
- [x] Test audio deletion
- [x] Test Notion integration
- [x] Test error handling

### Optimization & Refinement
- [x] Complete code comments
- [x] Add type hints
- [x] Performance optimization
- [x] Memory usage optimization
- [x] Error message optimization

### Documentation & Release
- [x] Write README.md
- [x] Add usage examples
- [x] Write troubleshooting guide
- [x] Add LICENSE
- [x] Create .gitignore
- [x] Initialize Git repository

---

## 🚀 Quick Start Examples

### Basic Usage

```bash
# Process single video
python src/main.py "https://youtube.com/watch?v=xxxxx"
python src/main.py -video "https://youtube.com/watch?v=xxxxx"

# Process playlist
python src/main.py -list "https://youtube.com/playlist?list=xxxxx"

# Process local MP3 folder
python src/main.py -local /path/to/mp3/folder

# Specify output format
python src/main.py -video "URL" --style detailed

# Keep audio files
python src/main.py -video "URL" --keep-audio

# Use cookies file (membership videos)
python src/main.py -video "URL" --cookies cookies.txt
```

### Python API Usage

```python
from src.main import process_video, process_playlist, process_local_folder
from pathlib import Path

# Process single video
result = process_video(
    url="https://youtube.com/watch?v=xxxxx",
    keep_audio=False,
    summary_style="detailed"
)

# Process playlist
results = process_playlist(
    playlist_url="https://youtube.com/playlist?list=xxxxx",
    keep_audio=False,
    summary_style="detailed"
)

# Process local MP3 folder
results = process_local_folder(
    folder_path=Path("/path/to/mp3/folder"),
    summary_style="detailed"
)

print(result['summary'])
print(result['notion_url'])
```

---

## 📊 Expected Output

### File Structure
```
output/
├── transcripts/
│   └── [video_id]_transcript.srt
├── summaries/
│   └── [video_id]_summary.md
└── reports/
    └── [timestamp]_[uploader]_[content-title].md
```

### Summary Format (Markdown)

```markdown
# Video Title

**Duration**: 15:30
**Generated**: 2025-10-29 10:30:00

## 📝 Content Summary
[3-5 sentences summarizing core content]

## 🎯 Key Points
- Point 1
- Point 2
- Point 3

## ⏱ Timeline
- 00:00 - Introduction
- 02:30 - Topic 1
- 08:15 - Topic 2
- 13:45 - Summary

## 💡 Core Insights
[In-depth analysis and insights]
```

---

## ⚠️ Important Notes

### Security & Compliance
- ⚠️ **DO NOT** commit `cookies.txt` to Git
- ⚠️ **DO NOT** share or redistribute membership content
- ⚠️ **USE ONLY** for personal learning
- ⚠️ Follow YouTube Terms of Service

### Performance Tips
- M2 Mac recommended to use `base` or `small` Whisper model
- Long videos (>1 hour) recommend using `tiny` or `base` model
- Watch for API rate limits when batch processing

### Troubleshooting
- **HTTP 403 Error**: Update yt-dlp (`pip install -U yt-dlp`)
- **Expired Cookies**: Re-export browser cookies
- **Slow Whisper**: Reduce model size or use `faster-whisper`
- **API Rate Limiting**: Add retry logic and delays

---

## 🔮 Future Extensions

### v2.0 Complete (Current)
- [x] YouTube playlist support
- [x] Local MP3 file support
- [x] Enhanced report naming with uploader and content title
- [x] Notion integration for knowledge management
- [x] English localization

### v3.0 Plans
- [ ] Add Web UI interface
- [ ] Support more video platforms (Bilibili, Vimeo)
- [ ] Multi-language translation features
- [ ] Export to PDF/Word formats
- [ ] Add video keyframe screenshots
- [ ] Integrate more AI model options

### v4.0 Vision
- [ ] Build local knowledge base
- [ ] Video content search
- [ ] Cross-video content correlation
- [ ] Auto-generate mind maps

---

## 📞 Support & Feedback

- **Issue Reports**: GitHub Issues
- **Feature Requests**: GitHub Discussions
- **Documentation**: README.md

---

## 📄 License

MIT License

---

**Last Updated**: 2025-11-01
**Maintainer**: [Yang Yu]
