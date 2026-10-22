# YouTube Transcription and Summarization

[Chinese README](doc/README_zh.md)

Process YouTube videos and playlists, scan a list of channels for recent uploads, or summarize MP3 files from a local folder. The tool uses existing YouTube subtitles when available and Whisper when transcription is needed, then writes a Markdown report locally and can optionally upload it to GitHub.

## Requirements

- Python 3.9 or newer
- FFmpeg
- An OpenRouter API key, or an installed and authenticated `agy` CLI

Whisper uses `mlx-whisper` automatically on Apple Silicon and `openai-whisper` on other platforms. Transcription models can require substantial memory and disk space.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `SUMMARY_PROVIDER` and its credential in `.env`:

- `openrouter_free` (default): set `OPENROUTER_API_KEY`.
- `agy_cli`: install and authenticate `agy`; no OpenRouter key is needed.

For GitHub uploads, also set `GITHUB_TOKEN` and `GITHUB_REPO` (`owner/repository`). `GITHUB_BRANCH` defaults to `main`. Without `--upload`, reports stay local.

## Usage

Run commands from the repository root with the virtual environment active. Summary style defaults to `detailed`; choose `brief` with `--style brief`.

```bash
# One YouTube video
python src/main.py -video "https://youtube.com/watch?v=VIDEO_ID"

# A playlist
python src/main.py -list "https://youtube.com/playlist?list=PLAYLIST_ID"

# MP3 files in a folder (not a single file)
python src/main.py -local ./audio_files

# A channel scan; one channel URL per line in channellist.txt
python src/main.py --scan channellist.txt --max-hours 4

# Upload reports after processing
python src/main.py -video "https://youtube.com/watch?v=VIDEO_ID" --upload

# Reprocess an item even if a completed report is already recorded
python src/main.py -video "https://youtube.com/watch?v=VIDEO_ID" --force
```

For membership or other login-restricted videos, pass a Netscape-format cookies file with `--cookies cookies.txt`. Browser-cookie use is opt-in with `--cookies-from-browser` (and optionally `--browser chrome|edge|firefox`).

Other CLI options include `--batch FILE` for a list of URLs or local paths, `--status`, `--list-failed`, `--list-resumable`, `--resume-only`, and `--daily-summary [YYYYMMDD]`. Run `python src/main.py --help` for the current full list.

## Channel scans

`--scan FILE` reads one channel URL per line. Blank lines and lines beginning with `#` are ignored. It considers videos published in the last two days, processes selected videos oldest-first, and writes a daily digest. A missing channel-list file is created with example entries; add channel URLs before scanning.

The scan has a single-instance lock at `logs/scan.lock`. `--max-hours` sets an in-process time budget; videos not started before the deadline are marked `PENDING_KILLED` and retried on a later scan. The partial digest is still written. `scripts/daily_scan.sh` is provided for scheduled runs; schedule it with your system's cron or task scheduler if desired.

## Output and tracking

```text
output/
├── transcripts/       # SRT transcripts
├── summaries/         # Intermediate summaries
└── summary/           # Final Markdown reports and daily_digest/

logs/
├── ytb_summary_track.db
├── two_time_fail.txt
└── *.log
```

The SQLite database `logs/ytb_summary_track.db` is the source of truth for completed-item reuse. A completed item is reused only when its recorded Markdown report still exists. YouTube items use their video ID; local MP3s use a content-derived ID based on the first 8 MB and file size, so renaming a file does not trigger another run. Use `--force` (or its alias `--no-reuse`) to bypass reuse.

The first database initialization can migrate completed records from the legacy `logs/run_track.db`, renaming it to `logs/run_track_backup.db`. New tracking writes go to `ytb_summary_track.db`.

## Configuration

Common `.env` settings:

- `SUMMARY_PROVIDER`, `OPENROUTER_API_KEY`, `MODEL_PRIORITY_1` through `MODEL_PRIORITY_3`, and `MODEL_FALLBACK` control summarization. OpenRouter tries configured models with retries for transient errors; `agy_cli` receives the complete SRT.
- `SUMMARY_LANGUAGE` selects `zh` or `en` (default `zh`). `--style` selects `brief` or `detailed`.
- `WHISPER_MODEL`, `WHISPER_LANGUAGE`, and `WHISPER_BACKEND` control transcription. `WHISPER_BACKEND=auto` selects MLX on Apple Silicon and OpenAI Whisper elsewhere.
- `GITHUB_TOKEN`, `GITHUB_REPO`, and `GITHUB_BRANCH` configure optional uploads.

See `.env.example` for the available settings and defaults. OpenRouter summaries are limited to 60,000 transcript characters; the tail is dropped with a warning. The `agy_cli` provider uses the full SRT.

## Development

Run the unit suite with:

```bash
python -m unittest discover tests
```

Tests use `unittest`; network and external-service calls should be mocked. Utility diagnostics are documented in [scripts/README.md](scripts/README.md).
