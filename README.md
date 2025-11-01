# YouTube Video Transcription & Summarization Tool

🎥 Automatically transcribe YouTube videos (including membership content) to text and generate AI-powered summaries

## ✨ Features

- ✅ Support for YouTube public and membership videos
- ✅ Automatic subtitle extraction or generation
- ✅ AI-powered video content summarization (using OpenRouter free models)
- ✅ Save storage space (optional audio deletion)
- ✅ Multiple summary styles (brief/detailed)
- ✅ Timestamped subtitle files (SRT format)
- ✅ YouTube playlist processing support
- ✅ Local MP3 file processing support
- ✅ Optional Notion integration for knowledge management

## 📋 System Requirements

- Python 3.9+
- FFmpeg 4.0+
- 8GB+ RAM (16GB recommended)
- OpenRouter API Key (free)

## 🚀 Quick Start

### 1. Install Dependencies

**Install FFmpeg**

```bash
# Mac
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org and add to PATH
```

**Install Python Dependencies**

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy environment template
cp .env.example .env

# Edit .env file and add your OpenRouter API Key
# OPENROUTER_API_KEY=your_api_key_here
```

**Get OpenRouter API Key:**
1. Visit [OpenRouter.ai](https://openrouter.ai/)
2. Sign up for free
3. Get API Key from settings page

### 3. Run the Program

**Method 1: Using Quick Scripts (Recommended)**

```bash
# Simple mode - just enter URL, uses defaults
./quick-run.sh

# Full mode - choose summary style, keep-audio options, etc.
./run.sh
```

**Method 2: Manual Execution**

```bash
# Activate virtual environment
source venv/bin/activate

# Basic usage - single video (default)
python src/main.py "https://youtube.com/watch?v=xxxxx"
python src/main.py -video "https://youtube.com/watch?v=xxxxx"

# YouTube playlist
python src/main.py -list "https://youtube.com/playlist?list=xxxxx"

# Local MP3 folder
python src/main.py -local /path/to/mp3/folder

# Brief summary
python src/main.py -video "URL" --style brief

# Keep audio files
python src/main.py -video "URL" --keep-audio

# Use cookies (for membership videos)
python src/main.py -video "URL" --cookies cookies.txt
```

## 📖 Usage Guide

### Command Line Arguments

```
python src/main.py [INPUT] [OPTIONS]

Input Arguments (mutually exclusive):
  -video URL             YouTube video URL (default if no flag specified)
  -list URL              YouTube playlist URL
  -local PATH            Local MP3 folder path

Optional Arguments:
  --cookies FILE         Path to cookies.txt file (for membership videos)
  --keep-audio          Keep downloaded audio files
  --style {brief|detailed}  Summary style (default: detailed)
```

### Processing Membership Videos

1. Install browser extension [Get cookies.txt](https://chrome.google.com/webstore/detail/get-cookiestxt/bgaddhkoddajcdgocldbbfleckgcbcid)
2. Log into YouTube
3. Export cookies as `cookies.txt`
4. Use `--cookies cookies.txt` parameter

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

print(f"Transcript file: {result['transcript_file']}")
print(f"Summary file: {result['summary_file']}")
print(f"Report file: {result['report_file']}")
print(f"Notion URL: {result['notion_url']}")
```

## 📁 Output Files

```
output/
├── transcripts/
│   └── [video_id]_transcript.srt      # Subtitle file
├── summaries/
│   └── [video_id]_summary.md          # Summary file (by video ID)
└── reports/
    └── [timestamp]_[uploader]_[title].md  # Report file (timestamped with uploader and title)
```

### Report File Format

Report filename format: `YYYYMMDD_HHMM_[uploader]_[content-title].md`

Example: `20251029_1535_TechChannel_introduction-to-python-programming.md`

File contains:
- Video title and duration
- AI-generated summary
- Reference information (video ID and URL)

### Summary File Format Example

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

## 💡 Core Insights
[In-depth analysis and insights]

---

## 📎 Reference Information

**Video ID**: `xxxxx`

**Video Link**: https://youtube.com/watch?v=xxxxx
```

## ⚙️ Configuration

Edit `.env` file for custom configuration:

```bash
# Whisper model size (tiny/base/small/medium/large)
WHISPER_MODEL=base

# Language setting (zh/en/auto)
WHISPER_LANGUAGE=zh

# Audio quality (kbps)
AUDIO_QUALITY=64

# Keep audio files
KEEP_AUDIO=false

# Notion Integration (optional)
NOTION_API_KEY=your_notion_integration_token
NOTION_DATABASE_ID=your_notion_database_id
```

**Model Selection Guide:**
- `tiny`: Fastest, lower accuracy (good for quick testing)
- `base`: Balanced speed and accuracy (recommended)
- `small`: More accurate, slower
- `medium/large`: Most accurate, requires more resources

## 🧪 Running Tests

```bash
# Run all tests
python -m unittest discover tests

# Run specific tests
python -m unittest tests.test_youtube
python -m unittest tests.test_transcriber
python -m unittest tests.test_summarizer
```

## ⚠️ Important Notes

### Security & Compliance
- ⚠️ **DO NOT** commit `cookies.txt` to Git
- ⚠️ **DO NOT** share or redistribute membership content
- ⚠️ **USE ONLY** for personal learning
- ⚠️ Follow YouTube Terms of Service

### Performance Tips
- For long videos (>1 hour), use `tiny` or `base` model
- Watch for API rate limits when batch processing
- First run downloads Whisper model (~150MB for base)

## 🐛 Troubleshooting

### HTTP 403 Error
```bash
# Update yt-dlp
pip install -U yt-dlp
```

### Expired Cookies
Re-export browser cookies

### Slow Whisper Transcription
- Use smaller model (`tiny` or `base`)
- Or install `faster-whisper` (optional)

### API Rate Limiting
Program will auto-retry. If frequent failures occur, wait and try later

### FFmpeg Not Found
Ensure FFmpeg is installed and added to system PATH

## 📚 Technology Stack

- **yt-dlp**: YouTube video downloading
- **OpenAI Whisper**: Speech-to-text transcription
- **OpenRouter**: AI text summarization
- **FFmpeg**: Audio processing
- **Notion API**: Knowledge management integration (optional)

## 🔮 Future Plans

- [ ] Support for batch processing multiple videos
- [ ] Web UI interface
- [ ] Support for more video platforms (Bilibili, Vimeo)
- [ ] Multi-language translation features
- [ ] Export to PDF/Word formats
- [ ] Video keyframe screenshots

## 📄 License

MIT License

---

**Last Updated**: 2025-11-01
