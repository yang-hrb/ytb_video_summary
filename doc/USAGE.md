# Quick Usage Guide

## 🚀 Running the Tool

### Option 1: Quick Run (Easiest)
Just paste the URL and go with default settings:

```bash
./quick-run.sh
```

When prompted, paste your YouTube URL (without quotes):
```
Paste YouTube URL:
https://youtube.com/watch?v=xxxxx
```

### Option 2: Full Control
Interactive script with all options:

```bash
./run.sh
```

You'll be asked to:
1. **Paste YouTube URL** (without quotes)
2. **Choose summary style** (brief/detailed) - default: detailed
3. **Keep audio?** (yes/no) - default: no
4. **Cookies file path** (for membership videos) - press Enter to skip

### Option 3: Manual Command
If you prefer direct control:

```bash
source venv/bin/activate
python src/main.py "YOUR_YOUTUBE_URL" --style detailed
```

---

## 📁 Output Files

After processing, check these directories:

```
output/
├── transcripts/        # [video_id]_transcript.srt
├── summaries/          # [video_id]_summary.md
└── reports/            # [timestamp]_[title].md
```

The **report file** (in `reports/`) is the most user-friendly - it's named with timestamp and video title.

---

## ⚙️ Script Features

### quick-run.sh
- ✓ Fastest way to run
- ✓ Uses sensible defaults
- ✓ Auto-activates venv
- ✓ Just paste URL and go

### run.sh
- ✓ Interactive prompts
- ✓ All command-line options
- ✓ Color-coded output
- ✓ Error checking
- ✓ Auto-activates venv

---

## 🔧 Configuration

All settings in `.env` file:

```bash
# Required
OPENROUTER_API_KEY=sk-or-v1-...

# Optional - good defaults provided
WHISPER_MODEL=base              # Model size
WHISPER_LANGUAGE=zh            # Language detection
AUDIO_QUALITY=64               # Download quality
KEEP_AUDIO=false              # Keep audio files
```

---

## 💡 Tips

1. **First run** downloads Whisper model (~150MB for base)
2. **Longer videos** (>1 hour) - consider using `tiny` model for speed
3. **Membership videos** - export cookies from browser, pass via `--cookies`
4. **FFmpeg** - auto-detected, but can set `FFMPEG_LOCATION` in .env if needed
5. **Check logs** - `youtube_summarizer.log` has detailed error info

---

## 🐛 Troubleshooting

### "No module named 'yt_dlp'"
→ Activate venv: `source venv/bin/activate`

### "FFmpeg not found"
→ Install: `brew install ffmpeg` (Mac) or `sudo apt install ffmpeg` (Linux)

### "401 Unauthorized" API error
→ Check your `OPENROUTER_API_KEY` in `.env` file
→ Key should start with `sk-or-v1-`
→ Get new key at https://openrouter.ai/settings/keys

### Scripts not executable
→ Run: `chmod +x run.sh quick-run.sh`

---

## 📞 Quick Examples

**Process a regular video:**
```bash
./quick-run.sh
# Paste: https://youtube.com/watch?v=xxxxx
```

**Membership video with cookies:**
```bash
./run.sh
# Paste URL
# Press Enter for defaults
# Enter cookies file path: cookies.txt
```

**Brief summary, keep audio:**
```bash
./run.sh
# Paste URL
# Style: brief
# Keep audio: yes
```
