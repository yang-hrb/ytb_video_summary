# AGENTS.md — ytb_video_summary

## Project Overview

Python CLI + FastAPI dashboard for downloading YouTube videos/podcasts, transcribing with Whisper, and generating AI summaries via OpenRouter or Xiaomi MiMo APIs.

## Key Commands

```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Set OPENROUTER_API_KEY or XIAOMI_API_KEY

# Run single video
python src/main.py "https://youtube.com/watch?v=xxxxx"

# Run from project root (required for all commands)
python src/main.py --help
python src/main.py --status
python src/main.py --list-failed
python src/main.py --resume-only

# Web dashboard (FastAPI on port 8999)
./dashboard.sh
# or: python -m uvicorn src.dashboard_app:app --host 0.0.0.0 --port 8999

# Tests (unittest, not pytest)
python -m unittest discover tests
python -m unittest tests.test_database  # single module

# Diagnostics (from project root, venv activated)
python scripts/diagnostics/diag_api_key.py
python scripts/diagnostics/diag_ffmpeg.py
```

## Architecture

### Entry Point & Pipeline

- `src/main.py` — CLI entry point, delegates to `src/cli/` for parsing/display
- `src/pipeline.py` — `ProcessingPipeline` class: download → transcribe → summarize → upload
- Pipeline tracks state in `run_track.db` (SQLite) with stages: `DOWNLOAD`, `TRANSCRIBE`, `SUMMARIZE`, `UPLOAD`
- Failed runs get status like `DOWNLOAD_FAILED`, `TRANSCRIBE_FAILED`, etc. (see `STAGE_TO_FAILED_STATUS`)

### Config Pattern

```python
from config import config  # NOT from config.settings
config.OPENROUTER_API_KEY  # singleton instance
config.resolve_whisper_backend()  # returns 'mlx' or 'openai'
```

- All config in `config/settings.py`, accessed via `config` singleton
- `.env` loaded automatically via `python-dotenv`
- Whisper backend: `auto` → `mlx` on Apple Silicon arm64, `openai` otherwise

### Exception Hierarchy

```python
from src.exceptions import PipelineError, DownloadError, TranscriptionError, ...
# All inherit from PipelineError
# Pipeline catches these to set correct *_FAILED status
```

### Database Layer

```python
from src.database import DatabaseManager
db = DatabaseManager(db_path)
with db.get_connection() as conn:
    conn.execute(...)
# Uses WAL mode, auto-commit, rollback on error
```

### Dynamic Prompts

- `config/prompt_profile_map.csv` maps uploader names to prompt types
- `config/prompt_types/{type}.txt` contains prompt templates (default, talk, education, live)
- `src/prompt_selector.py` selects prompt based on uploader

## File Structure

```
src/
├── main.py              # CLI entry point
├── pipeline.py          # ProcessingPipeline (core workflow)
├── database.py          # DatabaseManager (SQLite with WAL)
├── exceptions.py        # PipelineError hierarchy
├── run_tracker.py       # RunTracker (state machine in run_track.db)
├── transcriber.py       # Whisper (mlx or openai backend)
├── summarizer.py        # OpenRouter/Xiaomi API calls
├── youtube_handler.py   # yt-dlp wrapper
├── apple_podcasts_handler.py
├── channel_watcher.py   # Daemon for monitoring channels
├── daily_summary.py     # Daily digest generation
├── prompt_selector.py   # Dynamic prompt selection
├── batch_processor.py   # Batch processing logic
├── dashboard_app.py     # FastAPI app
├── dashboard_service.py # Dashboard API logic
├── job_manager.py       # Async job queue
├── zip_exporter.py      # ZIP bundle creation
├── github_handler.py    # GitHub upload integration
├── utils.py             # Helpers (sanitize_filename, get_category_folder)
└── cli/
    ├── parser.py        # argparse setup
    ├── commands.py      # Command dispatch
    └── display.py       # Console output formatting

config/
├── settings.py          # Config class (singleton)
├── prompt_types/        # Prompt templates (.txt)
└── prompt_profile_map.csv  # Uploader → prompt type mapping

tests/                   # unittest-based (NOT pytest)
scripts/                 # Shell scripts + diagnostics
web/                     # dashboard.html (static frontend)
output/                  # Generated (gitignored)
logs/                    # Log files (gitignored)
run_track.db             # SQLite state tracker (gitignored)
```

## Conventions

- **Language**: Bilingual codebase (Chinese comments/docstrings common, English for new code)
- **Indentation**: 4 spaces (PEP 8)
- **Naming**: `snake_case` functions/vars, `PascalCase` classes
- **Imports**: Use `from config import config` (not `from config.settings`)
- **Error handling**: No empty `except` blocks; always log errors
- **Database**: Use `DatabaseManager` for all SQLite ops (WAL mode enabled)
- **CLI output**: Use `src/cli/display.py` for user-facing messages

## Gotchas

- **Scripts must run from project root**: `scripts/*.sh` auto-cd to project root
- **Platform-conditional deps**: `mlx-whisper` only installs on Apple Silicon (arm64 macOS)
- **Cookies for member videos**: Use `--cookies-from-browser chrome` or provide `cookies.txt`
- **Run tracker**: `run_track.db` in `logs/` tracks all pipeline state; don't delete during runs
- **Prompt selection**: Check `config/prompt_profile_map.csv` before adding new uploader mappings
- **Dashboard static files**: `web/dashboard.html` served at `/dashboard`, API at `/api/*`

## Testing

- Framework: `unittest` (not pytest)
- Test files: `tests/test_*.py`
- Each test uses `tempfile` for isolation; cleans up in `tearDown`
- Run all: `python -m unittest discover tests`
- Run one: `python -m unittest tests.test_database`

## Recent Architecture (v2.1)

- SQLite state machine for pipeline tracking (smart resume)
- FastAPI dashboard with job queue and ZIP export
- Dynamic prompts based on uploader/channel
- Apple Silicon optimization (mlx-whisper)
- Daily digest and watchlist daemon
