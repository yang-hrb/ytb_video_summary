# YouTube Video Transcription & Summarization Tool

[中文文档 (Chinese README)](doc/README_zh.md)

🎥 Automatically transcribe YouTube videos (including membership content) to text and generate AI-powered summaries

## ✨ Features

- ✅ Support for YouTube public and membership videos
- ✅ Automatic subtitle extraction or generation
- ✅ AI-powered video content summarization (uses OpenRouter with a waterfall of models)
- ✅ **Configurable summary language** - Choose between Chinese (default) or English output via `.env` file
- ✅ **Language-aware transcription** - Whisper maintains original audio language
- ✅ Save storage space (optional audio deletion)
- ✅ Multiple summary styles (brief/detailed)
- ✅ Timestamped subtitle files (SRT format)
- ✅ YouTube playlist processing support
- ✅ Local MP3 file processing support
- ✅ **Apple Podcasts support** - Download and transcribe podcast episodes
- ✅ **Batch processing** - Process multiple inputs from a text file
- ✅ **Centralized logging system** - All logs saved to timestamped files in `logs/` folder
- ✅ **Individual file uploads** - Each processed file uploads to GitHub immediately to prevent batch failures

## 📊 Data Workflow

```
Input Sources → Processing Pipeline → Output & Storage
     ↓                  ↓                    ↓
  YouTube          1. Download          Local Files
  Playlist           Audio/Subs           (output/)
     or          2. Transcription            ↓
Apple Podcasts   3. AI Summary        GitHub Upload
     or          4. Save & Upload      (optional)
  Local MP3
   Folder
     or
  Batch File
 (mix of all)
```

**Processing Flow:**
1. **Input**: YouTube URL, Playlist, Apple Podcast, Local MP3 folder, or Batch file
2. **Transcription**: Whisper converts audio to text (preserves original language)
3. **Summarization**: OpenRouter AI generates summary using a waterfall of models (configurable output language)
4. **Output**: SRT transcript + Markdown summary + Enhanced report
5. **Upload**: Individual files uploaded to GitHub immediately after each success

**Key Benefits:**
- 🔄 **Individual file processing**: Each file uploads independently
- 🛡️ **Fault tolerance**: One file failure doesn't block others
- 📝 **Comprehensive logging**: All operations logged to timestamped files
- 🌐 **Language flexibility**: Transcription preserves original; summary language configurable

**Summarization Model Waterfall:**
The tool uses OpenRouter with a waterfall of models to ensure reliability:
1. **Primary Model**: DeepSeek R1 (via Chimera)
2. **Alternative Model**: Step-3.5-Flash
3. **Alternative Model**: Trinity-Large-Preview
4. **Fallback Model**: GPT-4o-Mini

## 📋 System Requirements

- Python 3.9+
- FFmpeg 4.0+
- 8GB+ RAM (16GB recommended)
- OpenRouter API Key for summarization (free options available)

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

# Edit .env file and configure your OpenRouter API Key
# OPENROUTER_API_KEY=your_api_key_here
```

**Get OpenRouter API Key (Free):**
1. Visit [OpenRouter.ai](https://openrouter.ai/)
2. Sign up for free
3. Get API Key from settings page
4. Add your key to `.env`: `OPENROUTER_API_KEY=your_api_key_here`

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

# Process batch input file (mix of URLs and paths)
./batch-run.sh
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

# Use local browser cookies (default, most reliable)
python src/main.py -video "URL" --cookies-from-browser

# Fallback to cookies.txt (less reliable across machines)
python src/main.py -video "URL" --no-cookies-from-browser --cookies cookies.txt

# Upload to GitHub (automatically during processing)
python src/main.py -video "URL" --upload
python src/main.py -list "URL" --upload
python src/main.py -local /path/to/mp3 --upload

# Apple Podcasts (single episode - latest)
python src/main.py --apple-podcast-single "https://podcasts.apple.com/..."

# Apple Podcasts (all episodes from show)
python src/main.py --apple-podcast-list "https://podcasts.apple.com/..."

# Batch processing (mix of URLs and paths)
python src/main.py --batch input.txt
python src/main.py --batch input.txt --style brief --upload
```

## 📖 Usage Guide

### Command Line Arguments

```
python src/main.py [INPUT] [OPTIONS]

Input Arguments (mutually exclusive):
  -video URL                      YouTube video URL (default if no flag specified)
  -list URL                       YouTube playlist URL
  --apple-podcast-single URL      Apple Podcasts URL (latest episode only)
  --apple-podcast-list URL        Apple Podcasts URL (all episodes from show)
  -local PATH                     Local MP3 folder path
  --batch FILE                    Batch input file (one URL or path per line)

Optional Arguments:
  --cookies FILE                  Path to cookies.txt file (fallback only)
  --cookies-from-browser / --no-cookies-from-browser
                                 Use local browser cookies (default: enabled)
  --browser {chrome,edge,firefox} Browser profile to read cookies from (default: chrome)
  --keep-audio                   Keep downloaded audio files (YouTube only)
  --style {brief|detailed}       Summary style (default: detailed)
  --upload                       Upload report files to GitHub repository
```

### Processing Membership Videos (Recommended)

1. Open Chrome on the same machine and log into YouTube.
2. Run with browser cookies (default):
   ```bash
   python src/main.py -video "URL" --cookies-from-browser
   ```
3. If browser cookies are unavailable, you can fall back to `cookies.txt`:
   ```bash
   python src/main.py -video "URL" --no-cookies-from-browser --cookies cookies.txt
   ```
> ⚠️ `cookies.txt` exports are often unreliable across machines and can trigger 403 errors.

### Python API Usage

```python
from src.main import process_video, process_playlist, process_local_folder
from pathlib import Path

# Process single video
result = process_video(
    url="https://youtube.com/watch?v=xxxxx",
    cookies_from_browser=True,
    browser="chrome",
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

### Batch Processing from Text File

Process multiple inputs (mix of YouTube videos, playlists, Apple Podcasts, and local MP3 folders) from a single text file:

**1. Create Batch Input File**

Create a text file (e.g., `input.txt`) with one input per line:

```text
# This is a comment - lines starting with # are ignored
# You can mix different input types in the same file

# YouTube video
https://www.youtube.com/watch?v=xxxxx

# YouTube playlist
https://www.youtube.com/playlist?list=xxxxx

# Apple Podcasts episode
https://podcasts.apple.com/us/podcast/podcast-name/id123456789

# Local MP3 folder
/path/to/mp3/folder
./audio_files
```

**2. Run Batch Processing**

```bash
# Using the helper script (recommended)
./batch-run.sh

# Or manually
python src/main.py --batch input.txt
python src/main.py --batch input.txt --style brief --upload
```

**Features:**
- ✅ **Auto-detection**: Automatically detects input type (YouTube, Apple Podcasts, local path)
- ✅ **Mixed inputs**: Process different types in a single batch
- ✅ **Comments support**: Lines starting with # are ignored
- ✅ **Error tolerance**: Failed items don't stop the batch processing
- ✅ **Progress tracking**: Shows detailed progress for each item
- ✅ **Summary report**: Final summary of successful and failed items

**Example Workflow:**
```
1. Create input.txt with your URLs and paths
2. Run: ./batch-run.sh
3. Choose summary style (brief/detailed)
4. Choose options (browser cookies, keep-audio, upload)
5. Processing starts... (shows progress for each item)
6. Done! Summary shows successful and failed items
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
- ✅ Optional browser cookies support for membership videos
- ✅ Processes all videos in playlist
- ✅ Asks for confirmation before GitHub upload
- ✅ Shows detailed progress and results

**Example workflow:**
```
1. Enter playlist URL
2. Choose summary style (brief/detailed)
3. Use browser cookies? (y/N)
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
│   └── [video_id]_transcript.srt      # Subtitle file (original language)
├── summaries/
│   └── [video_id]_summary.md          # Summary file (by video ID)
└── reports/
    └── [timestamp]_[uploader]_[title].md  # Report file (timestamped with uploader and title)

logs/
└── youtube_summarizer_[timestamp].log  # Detailed log file with timestamp
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
# === AI Model Configuration ===
# OpenRouter API key (required for summarization)
OPENROUTER_API_KEY=your_api_key_here

# OpenRouter model name
OPENROUTER_MODEL=deepseek/deepseek-r1

# === Whisper Configuration ===
# Whisper model size (tiny/base/small/medium/large)
WHISPER_MODEL=base

# Language setting for transcription (zh/en/auto)
# Note: Whisper preserves the original audio language
WHISPER_LANGUAGE=zh

# === Summary Language Configuration ===
# Output language for AI-generated summaries (zh/en)
# Default: zh (Chinese)
# - zh: Generates summaries in Chinese
# - en: Generates summaries in English
# Note: This controls ONLY the summary output language.
#       Transcription language is determined by the audio content.
SUMMARY_LANGUAGE=zh

# === Audio Configuration ===
# Audio quality (kbps)
AUDIO_QUALITY=64

# Keep audio files after processing
KEEP_AUDIO=false

# === GitHub Upload Configuration (Optional) ===
# GitHub personal access token (requires 'repo' scope)
GITHUB_TOKEN=your_github_token_here

# Target repository (format: username/repo)
GITHUB_REPO=username/repository_name

# Target branch (default: main)
GITHUB_BRANCH=main

# === Logging Configuration ===
# All logs are saved to timestamped files in logs/ folder
# Console output shows INFO level and above
# Log files contain DEBUG level and above
```

**Model Selection Guide:**
- `tiny`: Fastest, lower accuracy (good for quick testing)
- `base`: Balanced speed and accuracy (recommended)
- `small`: More accurate, slower
- `medium/large`: Most accurate, requires more resources

**Language Configuration:**
- **WHISPER_LANGUAGE**: Controls audio transcription language detection (original audio language is preserved)
- **SUMMARY_LANGUAGE**: Controls AI summary output language (zh=Chinese, en=English)
  - Set to `zh` for Chinese summaries (default)
  - Set to `en` for English summaries
  - Transcripts always maintain the original audio language

**GitHub Upload Configuration:**
To enable automatic GitHub uploads after processing:
1. Create a GitHub Personal Access Token with `repo` scope
2. Add the following to your `.env` file:
   ```bash
   GITHUB_TOKEN=your_token_here
   GITHUB_REPO=username/repo_name
   GITHUB_BRANCH=main
   ```
3. Use `--upload` flag or the automated scripts (`playlist-to-github.sh`, `local-mp3-to-github.sh`)

**Important Upload Behavior:**
- Each file is uploaded to GitHub **immediately after successful processing**
- This prevents one file failure from blocking other uploads
- If a file fails to process, it's skipped and processing continues with the next file
- Failed uploads are logged but don't stop the workflow

## 🧪 Running Tests

```bash
# Run all tests
python -m unittest discover tests

# Run specific tests
python -m unittest tests.test_youtube
python -m unittest tests.test_transcriber
python -m unittest tests.test_summarizer
```

## 📋 Logging System

The application features a comprehensive logging system:

**Log Locations:**
- **Console**: INFO level and above (user-friendly progress messages)
- **Log Files**: DEBUG level and above (detailed technical information)
  - Location: `logs/youtube_summarizer_[YYYYMMDD_HHMMSS].log`
  - Format: `2025-11-02 15:30:45 - INFO - [Module] Message`

**Log Contents:**
- Processing steps and progress
- API requests and responses
- File operations (read/write/upload)
- Error details with stack traces
- GitHub upload status
- Performance metrics

**Benefits:**
- 🔍 **Debugging**: Detailed logs help troubleshoot issues
- 📊 **Audit Trail**: Complete record of all operations
- 🕐 **Timestamped**: Each session gets a unique log file
- 🎯 **Dual Output**: Console shows key info, files show everything

## ⚠️ Important Notes

### Security & Compliance
- ⚠️ **DO NOT** commit `cookies.txt` to Git
- ⚠️ **Prefer browser cookies** on the same machine; exported cookies often trigger 403s
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
Then ensure you're logged into YouTube in Chrome and run with `--cookies-from-browser`.

### Expired Cookies
Log back into YouTube in Chrome and rerun with `--cookies-from-browser`

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
- [x] Configurable summary language (Chinese/English)
- [x] Centralized logging system with timestamped log files
- [x] GitHub repository integration for automated backup
- [x] Individual file upload to prevent batch failures
- [ ] Web UI interface
- [ ] Support for more video platforms (Bilibili, Vimeo)
- [ ] Multi-language translation features
- [ ] Export to PDF/Word formats
- [ ] Video keyframe screenshots

## 📄 License

MIT License

---

**Last Updated**: 2025-11-02

## 📝 Recent Changes (2025-11-02)

### Centralized Logging System
- ✅ Replaced all `print()` statements with structured logging
- ✅ Dual output: Console (INFO+) and log files (DEBUG+)
- ✅ Timestamped log files in `logs/` folder
- ✅ Comprehensive error tracking and debugging information

### Individual File Upload
- ✅ Each file uploads to GitHub immediately after processing
- ✅ Prevents one failure from blocking other uploads
- ✅ Improved fault tolerance for batch operations
- ✅ Works with playlists and local MP3 folders

### Configurable Summary Language
- ✅ New `SUMMARY_LANGUAGE` option in `.env` file
- ✅ Choose between Chinese (zh) or English (en) summaries
- ✅ Default: Chinese (zh)
- ✅ Transcription always preserves original audio language

### Environment Configuration Updates
- ✅ Added `SUMMARY_LANGUAGE` setting (zh/en)
- ✅ Enhanced GitHub configuration documentation
- ✅ Improved comments and organization in `.env.example`
