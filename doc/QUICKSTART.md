# Quick Start Guide

## 🎯 Project Setup Complete!

All necessary files and directory structure have been generated. Here are the steps to get started:

## 📋 Next Steps

### 1. Install FFmpeg (Required)

**Windows:**
```cmd
# Download from https://ffmpeg.org/download.html
# Extract and add to system PATH
```

**Mac:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg
```

### 2. Setup Python Environment

```cmd
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure API Key

```cmd
# Copy environment template
copy .env.example .env

# Edit .env file and add your OpenRouter API Key
notepad .env
```

**Get OpenRouter API Key:**
1. Visit https://openrouter.ai/
2. Sign up for free
3. Get API Key from settings page
4. Add API Key to `.env` file

### 4. Test Run

```cmd
# Test with a short video
python src\main.py "https://youtube.com/watch?v=xxxxx"

# Or use brief summary mode
python src\main.py "URL" --style brief
```

## 📁 Project Structure

```
ytb_video_summary/
├── config/                 # Configuration module
│   ├── __init__.py
│   └── settings.py        # Environment variables and path configuration
│
├── src/                   # Source code
│   ├── __init__.py
│   ├── main.py           # Main program entry
│   ├── youtube_handler.py # YouTube downloader
│   ├── transcriber.py    # Whisper transcription
│   ├── summarizer.py     # AI summarization
│   ├── notion_handler.py # Notion integration
│   └── utils.py          # Utility functions
│
├── tests/                # Unit tests
│   ├── test_youtube.py
│   ├── test_transcriber.py
│   └── test_summarizer.py
│
├── output/               # Output directory
│   ├── transcripts/      # Subtitle files
│   ├── summaries/        # Summary files (by video ID)
│   └── reports/          # Report files (timestamped with title)
│
├── temp/                 # Temporary audio files
├── .env.example         # Environment variable template
├── .gitignore           # Git ignore configuration
├── requirements.txt     # Python dependencies
├── README.md           # Project documentation
└── prd.md              # Product requirements document
```

## 🔧 Configuration Options

Customize the following options in `.env` file:

```bash
# Whisper model (tiny/base/small/medium/large)
WHISPER_MODEL=base

# Language (zh/en/auto)
WHISPER_LANGUAGE=zh

# Audio quality (kbps)
AUDIO_QUALITY=64

# Keep audio files
KEEP_AUDIO=false

# Notion Integration (optional)
NOTION_API_KEY=your_notion_integration_token
NOTION_DATABASE_ID=your_notion_database_id
```

## 🎬 Usage Examples

### Basic Usage
```cmd
python src\main.py "https://youtube.com/watch?v=dQw4w9WgXcQ"
```

### Membership Videos (requires cookies)
```cmd
# 1. Export cookies.txt using browser extension
# 2. Place cookies.txt in project root
# 3. Run command
python src\main.py "URL" --cookies cookies.txt
```

### Keep Audio Files
```cmd
python src\main.py "URL" --keep-audio
```

### Brief Summary
```cmd
python src\main.py "URL" --style brief
```

### YouTube Playlist
```cmd
python src\main.py -list "https://youtube.com/playlist?list=xxxxx"
```

### Local MP3 Folder
```cmd
python src\main.py -local /path/to/mp3/folder
```

## 🧪 Running Tests

```cmd
# Run all tests
python -m unittest discover tests

# Run specific tests
python -m unittest tests.test_youtube
```

## 📊 Output Description

After processing, the following files are generated:

1. **Subtitle File**: `output/transcripts/[video_id]_transcript.srt`
   - Timestamped subtitles
   - SRT format

2. **Summary File**: `output/summaries/[video_id]_summary.md`
   - Markdown format
   - Named by video ID

3. **Report File**: `output/reports/[timestamp]_[uploader]_[content-title].md`
   - Markdown format
   - Named with timestamp, uploader, and content title
   - Includes video ID and URL as reference
   - Example: `20251029_1535_TechChannel_introduction-to-python.md`

## ⚠️ Common Issues

### 1. Missing FFmpeg
**Error**: `ffmpeg not found`
**Solution**: Install FFmpeg and add to system PATH

### 2. API Key Not Set
**Error**: `OpenRouter API key is required`
**Solution**: Set `OPENROUTER_API_KEY` in `.env` file

### 3. First Run is Slow
**Reason**: Whisper needs to download model file (~150MB for base)
**Note**: This is normal and only happens on first run

### 4. HTTP 403 Error
**Solution**: Update yt-dlp
```cmd
pip install -U yt-dlp
```

## 📚 More Resources

- **Full Documentation**: See `README.md`
- **Product Requirements**: See `prd.md`
- **GitHub Issues**: Report issues or suggestions

## 🎉 Start Using!

You're now ready to start using this tool. Enjoy!

---

If you have questions, please check README.md or submit a GitHub Issue.
