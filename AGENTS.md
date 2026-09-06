# AGENTS.md

## Project

YouTube/podcast transcription & summarization tool. Downloads audio from YouTube (incl. membership), Apple Podcasts, or local MP3 → transcribes via Whisper → summarizes via OpenRouter model waterfall → saves reports locally and optionally uploads to GitHub.

Three source types: **youtube** (video/playlist), **podcast** (single/show), **local** (folder of MP3s).

## Data / Workflow

```
Input Source                Processing Pipeline                     Output
────────────                ───────────────────                     ──────
YouTube URL          ┌──────────────────────────────────────┐   transcripts/*.srt
  │ or playlist      │ ProcessingPipeline (src/pipeline.py) │   summaries/*_summary.md
  │ or Apple Podcast │                                      │   reports/*.md
  │ or local MP3 dir │ 1. Download (yt-dlp / feedparser)    │   (optionally) GitHub upload
  │ or batch file    │    ↓ stage='download'                │
  │ or web dashboard │ 2. Transcribe (Whisper)              │   run_track.db
  └────────────────→│    ↓ stage='transcribe'              │   (SQLite state tracker)
                     │ 3. Summarize (OpenRouter waterfall)  │
                     │    ↓ stage='summarize'               │
                     │ 4. Upload report (GitHub, optional)  │
                     │    ↓ stage='upload'                  │
                     │ 5. Save to run_track.db              │
                     └──────────────────────────────────────┘
                          ↑ Status tracked per stage      ↑ Smart resume:
                          status ∈ {PENDING, DOWNLOADING,   --resume-only picks up from
                          TRANSCRIBING, TRANSCRIPT_READY,   last failed stage without
                          SUMMARIZING, SUMMARY_READY,        re-downloading audio
                          COMPLETED, *_FAILED}
```

## Essential Commands

```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # set OPENROUTER_API_KEY

# Run (entrypoint)
python src/main.py "https://youtube.com/watch?v=xxxxx"
python src/main.py --help

# Dashboard (FastAPI on 127.0.0.1:8999/dashboard)
./dashboard.sh                        # or: uvicorn src.dashboard_app:app --reload --port 8999

# Test
python -m unittest discover tests      # all 40 tests
python -m unittest tests.test_database # single module
```

## Architecture — What's Non-Obvious

- **`ProcessingPipeline`** (`src/pipeline.py`) is the central orchestrator. It wraps download→transcribe→summarize→upload in a SQLite-tracked state machine. Every item (video, MP3, podcast episode) goes through one pipeline instance. The `resume()` static method re-animates failed runs from their last stage.

- **`ProcessingPipeline` accepts a shared `Transcriber`** to avoid reloading Whisper per-item in batches. Batch modules (`src/batch.py`) use `_make_shared_transcriber()` to pre-warm the model once.

- **Two Whisper backends** (`src/transcriber.py`): `mlx-whisper` on Apple Silicon (arm64 macOS), `openai-whisper` everywhere else. Controlled by `WHISPER_BACKEND=auto|mlx|openai`. The mlx backend auto-falls back to openai if the mlx package is missing.

- **Config singleton**: `from config import config` gives you the `Config` instance from `config/settings.py`. It reads all env vars on import, validates `OPENROUTER_API_KEY`, and auto-creates output directories.

- **`from config import config` works because `src/main.py` inserts project root into `sys.path`** on line 13-15. Test files do the same manually.

- **Smart resume status map** (`RunTracker.RESUMABLE_STATUS_MAP`):
  - `DOWNLOAD_FAILED` → full re-process needed (no audio saved)
  - `TRANSCRIBE_FAILED` → re-transcribe if audio file exists
  - `TRANSCRIPT_READY` / `SUMMARIZE_FAILED` → re-summarize from existing SRT
  - `SUMMARY_READY` / `UPLOAD_FAILED` → re-upload existing report

- **Dynamic prompts** (`src/prompt_selector.py`): Reads `config/prompt_profile_map.csv` (uploader→prompt_type mapping) and picks a random prompt from `config/prompt_types/{type}.txt`. Each type file can have multiple prompts separated by `---`.

- **Batch modules are split across two files**: `src/batch_processor.py` has the generic `BatchProcessor[T,R]` dataclass-driven processor. `src/batch.py` has the concrete batch orchestration for playlists, podcast shows, local folders, and mixed batch files.

- **Web dashboard** (`src/dashboard_app.py`): FastAPI served via uvicorn. Uses `DashboardService`, `JobManager`, and `ZipExporter`. The HTML is a single-file vanilla JS dashboard at `web/dashboard.html`.

- **GitHub upload path**: `summary/<category_letter>/<uploader_slug>/YYYY_MM/filename`. Category is derived from the uploader name's first character for alphabetical grouping.

- **Failure log**: One file per process session (`logs/failures_{timestamp}.txt`), not one file per failure (prevents 80+ files). Auto-cleaned after 30 days via `cleanup_old_logs()`.

## Conventions

- Use `PipelineError` subclasses from `src/exceptions.py` for project exceptions (`DownloadError`, `TranscriptionError`, `SummarizationError`, `UploadError`, `ConfigurationError`, `PodcastError`, `DatabaseError`, `ValidationError`, `ExternalServiceError`).
- Use `DatabaseManager` for all SQLite operations — provides WAL mode, context manager connections, and raises `DatabaseError`.
- All console output goes through `src/cli/display.py` functions. The `CommandHandler` in `src/cli/commands.py` dispatches parsed args.
- `logger = logging.getLogger(__name__)` per module using the `ytb_summarizer` logger hierarchy. `src/logger.py` sets up colored console + file handlers.
- Tests in `tests/` use `unittest` framework. Database tests create temp files in `setUp`/`tearDown`. Avoid real API calls.

## Testing

- Run `python -m unittest discover tests` — 40 tests, all passing.
- Test files: `test_database.py`, `test_run_tracker.py`, `test_summarizer.py`, `test_summarizer_fallback.py`, `test_transcriber.py`, `test_youtube.py`, `test_batch_processor.py`, `test_file_storage.py`, `test_prompt_selector.py`, `test_dashboard.py`.
- `test_dashboard.py` starts an actual HTTP server and hits the API — skip it for quick feedback loops.
- New tests: `tests/test_<topic>.py` with `test_<behavior>` method names.

## Agent skills

### Issue tracker

Issues live as local markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context (one `CONTEXT.md` + `docs/adr/` at the repo root). See `docs/agents/domain.md`.
