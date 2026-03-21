# YouTube Video Transcription & Summarization Tool

[中文文档 (Chinese README)](doc/README_zh.md)

🎥 Automatically transcribe YouTube videos (including membership content) to text and generate AI-powered summaries

## ✨ Features

- ✅ Support for YouTube public and membership videos
- ✅ Automatic subtitle extraction or AI transcription (Whisper)
- ✅ **Apple Silicon Optimization** - Native support for `mlx-whisper` for lightning-fast transcription on M1/M2/M3 Macs.
- ✅ AI-powered video content summarization (uses OpenRouter with a waterfall of models)
- ✅ **Dynamic Prompting** - Uses specific AI prompts based on the uploader/channel to tailor summaries.
- ✅ **Web Dashboard UI (FastAPI)** - Built-in graphical interface to submit jobs, monitor execution, and download ZIP bundles containing reports and transcripts.
- ✅ **Smart Resume & State Tracking** - SQLite-backed pipeline state machine allows safely resuming failed jobs (e.g., from `TRANSCRIBE_FAILED` or `SUMMARIZE_FAILED`) without redownloading.
- ✅ **Watchlist & Daily Digest** - Background daemon to automatically track new videos from your favorite channels and generate a daily Markdown digest report.
- ✅ **Apple Podcasts & Local MP3** support
- ✅ Configurable summary language (Chinese/English) via `.env`
- ✅ Batch processing from a text file or YouTube playlist
- ✅ Optional automated GitHub uploads for backup

## 📊 Data Workflow

```
Input Sources → Processing Pipeline (SQLite Tracked) → Output & Storage
      ↓                       ↓                                 ↓
   YouTube               1. Download                     Local Files
   Playlist                Audio/Subs                 (Reports, Transcripts)
      or                 2. Transcription                       ↓
Apple Podcasts           3. AI Summary                    Zip Bundle Export
      or                 4. Save & Upload               (via Dashboard) 
   Local MP3                     ↑                              ↓
     or                  5. Status Updated                GitHub Upload
  Web Job Queue                                            (optional)
```

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
```

**Install Python Dependencies**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
# Edit .env file and configure your OPENROUTER_API_KEY
```

### 3. Run the Web Dashboard (Recommended)

Start the built-in FastAPI dashboard to easily manage your processing jobs:

```bash
./start_dashboard.sh
```
Then visit **[http://127.0.0.1:8999/dashboard](http://127.0.0.1:8999/dashboard)** in your browser!
- Submit single videos or full playlists.
- Track success/failure statistics.
- Download complete ZIP bundles containing your summaries and transcripts.

### 4. Run via CLI

```bash
# Basic usage - single video
python src/main.py "https://youtube.com/watch?v=xxxxx"

# Process YouTube playlist
python src/main.py -list "https://youtube.com/playlist?list=xxxxx"

# Watchlist Daemon - monitor channels automatically
python src/main.py --watch-daemon --watch-time 3600

# Daily Summary Generation
python src/main.py --daily-summary

# Resume failed jobs intelligently
python src/main.py --resume-only

# Diagnostics
python src/main.py --status
python src/main.py --list-failed
```

## 📖 Usage Guide

### Command Line Arguments

```
Input Arguments (mutually exclusive):
  -video URL                      YouTube video URL
  -list URL                       YouTube playlist URL
  --apple-podcast-single URL      Apple Podcasts URL (latest episode)
  --apple-podcast-list URL        Apple Podcasts URL (all episodes)
  -local PATH                     Local MP3 folder path
  --batch FILE                    Batch input file

Diagnostic & State Commands:
  --status                        Display processing statistics
  --list-failed                   List failed runs and reasons
  --list-resumable                List runs that can be resumed
  --resume-only                   Resume failed or stalled runs

Watchlist & Summary Commands:
  --watch-daemon                  Run the channel watcher continuously
  --watch-run-once                Execute a single watch scan
  --import-watchlist FILE         Import channels from text file
  --daily-summary                 Generate daily summary digest

Optional Arguments:
  --cookies-from-browser          Use local browser cookies (highly recommended)
  --browser {chrome,edge,firefox} Specify browser to read cookies from
  --style {brief|detailed}        Summary style (default: detailed)
  --upload                        Upload report files to GitHub
```

### Automated GitHub Processing & Watchlist
If you configure `GITHUB_TOKEN`, `GITHUB_REPO`, and `GITHUB_BRANCH` in `.env`, appending `--upload` to commands uploads generated assets directly to GitHub immediately upon completion.
The system also intelligently skips redundant processing by checking the historic completion statuses using `run_track.db`.

## 📁 Output Files

```text
output/
├── transcripts/
│   └── [video_id]_transcript.srt      # Subtitle file
├── summaries/
│   └── [video_id]_summary.md          # Summary file 
├── reports/
│   └── [timestamp]_[uploader]_[title].md  # Finished Report (Timestamped)
└── zips/
    └── summary_bundle_job_*.zip       # Batch UI Zip Export

logs/
└── ytb_summarizer_[timestamp].log     # Detailed logs
run_track.db                           # SQLite Pipeline Tracker
```

## ⚙️ Configuration

Key options available in `.env`:
- `WHISPER_BACKEND`: `auto` uses `mlx-whisper` for Apple Silicon; forces standard `openai-whisper` otherwise.
- `SUMMARY_LANGUAGE`: `zh` (Chinese) or `en` (English).
- `OPENROUTER_MODEL` & `MODEL_PRIORITY_{1..3}`: Allows setup of a resilient waterfall of summarization models, gracefully failing over in case of a 429 or 500 error.

## 🔮 Future Plans

- [x] Support for batch processing multiple videos
- [x] Local audio file and podcast support
- [x] Centralized logging system
- [x] GitHub repository integration
- [x] Advanced SQLite State Tracker & Smart Resume
- [x] Web UI interface & Dashboard ZIP Export
- [x] Dynamic uploader-based prompts & Daily Digest
- [ ] Support for more video platforms (Bilibili, Vimeo)
- [ ] Multi-language translation features
- [ ] Export to PDF/Word formats
- [ ] Video keyframe screenshots

---

**Last Updated**: 2026-03-20

## 📝 Recent Changes (v2.1 / 2026-03 Update)

Extensive Phase 1 - 4 improvements focusing on reliability, observability, and usability:
- ✅ **Web UI Dashboard**: FastAPI-driven UI serving jobs, displaying stats and fetching batched summary ZIP bundles.
- ✅ **SQLite State Machine**: Robust tracking of pipeline stages (`DOWNLOAD`, `TRANSCRIBE`, `SUMMARIZE`, etc.), radically enhancing batch stability allowing for resuming halfway via `--resume-only`.
- ✅ **Daily Digest & Watchlists**: Supports cron/daemon based tracking of new videos per channel, avoiding repetition natively through `.db` queries, and automatically generating an easily readable `daily_digest` markup.
- ✅ **Dynamic Prompts**: Added semantic detection (e.g. Talk show, Education, Live) via CSV maps altering instructions parsed to OpenRouter dynamically based on the uploader.
- ✅ **Apple Silicon Boost**: Refactored Python backend bindings to initialize `mlx-whisper` explicitly for Apple Silicon architectures dramatically bypassing Whisper's prior overhead.
