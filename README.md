# YouTube Video Transcription & Summarization Tool

[中文文档 (Chinese README)](doc/README_zh.md)

🎥 Automatically transcribe YouTube videos (including membership content) to text and generate AI-powered summaries

## ✨ Features

- ✅ Support for YouTube public and membership videos
- ✅ Automatic subtitle extraction or generation
- ✅ AI-powered video content summarization (using OpenRouter free models)
- ✅ **Language-aware AI summaries** - Automatically generates summaries in the same language as the content (Chinese→Chinese, English→English)
- ✅ Save storage space (optional audio deletion)
- ✅ Multiple summary styles (brief/detailed)
- ✅ Timestamped subtitle files (SRT format)
- ✅ YouTube playlist processing support
- ✅ Local MP3 file processing support

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

# Process YouTube playlist and upload to GitHub
./playlist-to-github.sh

# Process local MP3 folder and upload to GitHub
./local-mp3-to-github.sh
```

**Features of GitHub Upload Scripts:**
- 🎯 **Automated workflow**: Process content and upload in one command
- 🎨 **Interactive prompts**: Guides you through all options
- 📊 **Progress tracking**: Shows processing and upload status
- ✅ **Smart confirmation**: Asks before uploading to GitHub
- 🛡️ **Error handling**: Saves locally if GitHub upload fails

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

# Upload to GitHub (automatically during processing)
python src/main.py -video "URL" --upload
python src/main.py -list "URL" --upload
python src/main.py -local /path/to/mp3 --upload
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
  --keep-audio          Keep downloaded audio files (YouTube only)
  --style {brief|detailed}  Summary style (default: detailed)
  --upload              Upload report files to GitHub repository
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
```

### Automated Playlist & MP3 Processing with GitHub Upload

Use the automated shell scripts for a streamlined workflow:

**1. YouTube Playlist to GitHub (`playlist-to-github.sh`)**

Process an entire YouTube playlist and automatically upload reports to GitHub:

```bash
# Interactive mode (prompts for all options)
./playlist-to-github.sh

# With playlist URL as argument
./playlist-to-github.sh "https://youtube.com/playlist?list=xxxxx"
```

**Features:**
- ✅ Prompts for playlist URL
- ✅ Choose summary style (brief/detailed)
- ✅ Optional cookies support for membership videos
- ✅ Processes all videos in playlist
- ✅ Asks for confirmation before GitHub upload
- ✅ Shows detailed progress and results

**Example workflow:**
```
1. Enter playlist URL
2. Choose summary style (brief/detailed)
3. Use cookies? (y/N)
4. Processing playlist... (shows progress for each video)
5. Upload reports to GitHub? (Y/n)
6. Done! Reports uploaded to GitHub
```

**2. Local MP3 to GitHub (`local-mp3-to-github.sh`)**

Process local MP3 files and automatically upload reports to GitHub:

```bash
# Interactive mode (prompts for folder path)
./local-mp3-to-github.sh

# With folder path as argument
./local-mp3-to-github.sh /path/to/mp3/folder
```

**Features:**
- ✅ Prompts for MP3 folder path
- ✅ Validates folder and counts MP3 files
- ✅ Choose summary style (brief/detailed)
- ✅ Processes all MP3 files with transcription
- ✅ Asks for confirmation before GitHub upload
- ✅ Shows detailed progress and results

**Example workflow:**
```
1. Enter MP3 folder path
2. Found 10 MP3 file(s) in folder ✓
3. Choose summary style (brief/detailed)
4. Processing MP3 files... (shows progress)
5. Upload reports to GitHub? (Y/n)
6. Done! Reports uploaded to GitHub
```

**Prerequisites for GitHub Upload:**
- GitHub must be configured in `.env` file:
  ```bash
  GITHUB_TOKEN=your_personal_access_token
  GITHUB_REPO=username/repository_name
  GITHUB_BRANCH=main
  ```
- If not configured, reports will be saved locally only

### GitHub Batch Upload

Upload all markdown files from a folder to your GitHub repository using the dedicated upload script:

**Setup:**
```bash
# Configure GitHub in .env file
GITHUB_TOKEN=your_personal_access_token
GITHUB_REPO=username/repository_name
GITHUB_BRANCH=main
```

**Usage:**
```bash
# Upload all .md files from output/reports to GitHub
python src/upload_to_github.py output/reports

# Upload to a different remote folder
python src/upload_to_github.py output/summaries --remote-folder summaries

# Preview what would be uploaded (dry run)
python src/upload_to_github.py output/reports --dry-run
```

**Features:**
- 📤 Uploads all .md files from specified folder
- 🔄 Automatically creates or updates files in GitHub
- 📊 Shows upload progress and summary
- ✅ Interactive confirmation before upload
- 🛡️ Dry-run mode to preview changes

**Example Output:**
```
Found 15 markdown files:
  - 20251101_1430_TechChannel_intro-to-ai.md
  - 20251101_1445_DevTips_python-best-practices.md
  ...

Ready to upload 15 files to GitHub
Repository: username/video-summaries
Branch: main
Remote folder: reports

Continue? [y/N]: y

[1/15] Uploading: 20251101_1430_TechChannel_intro-to-ai.md
✓ Uploaded successfully
  URL: https://github.com/username/video-summaries/blob/main/reports/...

Upload Summary:
Total files: 15
Successful: 15
✓ All files uploaded successfully!
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

## 🔮 Future Plans

- [x] Support for batch processing multiple videos (YouTube playlists)
- [x] Local audio file processing support
- [x] Language-aware AI summaries
- [ ] GitHub repository integration for automated backup
- [ ] Web UI interface
- [ ] Support for more video platforms (Bilibili, Vimeo)
- [ ] Multi-language translation features
- [ ] Export to PDF/Word formats
- [ ] Video keyframe screenshots

## 📄 License

MIT License

---

**Last Updated**: 2025-11-01
