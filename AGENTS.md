# AGENTS.md

YouTube transcription & summarization tool. YouTube video/playlist/channel-scan or local MP3 folder → download → Whisper transcribe → OpenRouter waterfall summarize → local report + optional GitHub upload. Podcast and dashboard were deleted (Sep 2026); do not re-add.

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then set OPENROUTER_API_KEY (required for every run)
```

- Env is read from repo-root `.env` via `load_dotenv()` in `config/settings.py`: `OPENROUTER_API_KEY` (required), `GITHUB_TOKEN` / `GITHUB_REPO` (only needed with `--upload`).
- Without `OPENROUTER_API_KEY` every CLI command exits 1 (`config.validate()` in `CommandHandler.execute()`).

## The four commands (Hermes entry points)

Canonical flags on all four: `--style detailed --cookies cookies.txt --upload` (omit `--cookies` if no `cookies.txt`; `--cookies-from-browser` defaults to disabled). `--style` defaults to `detailed`.

```bash
source venv/bin/activate
python src/main.py -video "https://youtube.com/watch?v=xxxxx" --style detailed --cookies cookies.txt --upload
python src/main.py -list "https://youtube.com/playlist?list=xxxxx" --style detailed --cookies cookies.txt --upload
python src/main.py -local ./audio_files --style detailed --upload
python src/main.py --scan channellist.txt --style detailed --cookies cookies.txt --upload --max-hours 4
```

- `-local PATH` takes a folder of MP3s (e.g. `./audio_files`), not a single file.
- `--scan FILE` reads `channellist.txt` (one channel URL per line, `#` comments skipped) and only runs videos published in the last 2 days. Daily cron wraps it: `scripts/daily_scan.sh` (`0 4 * * * .../scripts/daily_scan.sh`, `--max-hours 4`, single-instance via `logs/scan.lock`).
- `--force` / `--no-reuse` forces re-processing even when a COMPLETED report exists.
- `python src/main.py --help` shows all of the above.

## Dedup DB (the only "done before?" source)

`logs/ytb_summary_track.db`, single table (auto-created + auto-migrated on first use):

```sql
videos(video_id PK, url, channel_url, publish_date, first_seen, md_path,
       github_url, status, fail_count, last_error, updated_at,
       uploader, title, duration_seconds)
-- video_id: YouTube 11-char id, or local_<sha256(content)[:16]> for MP3s
--   (first 8 MB + file size hashed; renaming never re-runs, 1 changed byte does)
-- status ∈ {COMPLETED, FAILED, PENDING_KILLED}
```

- COMPLETED hit → old MD path is reused and referenced in the Digest, zero download/transcribe/summarize, zero GitHub writes. `logs/run_track.db` is a frozen legacy backup, never written; do not read it for status.
- Legacy migration is automatic (`logs/run_track.db` → `logs/run_track_backup.db`, COMPLETED rows imported once via `migrate_legacy_db()`).

## Failures: where to look

- `logs/two_time_fail.txt` — one CSV line per video on its 2nd failure: `video_id,url,第一次失败时间,第二次失败时间,错误`.
- Daily Digest (`generate_daily_summary(target_date=startup day)`) top red section `🔴 Failures` lists all `fail_count >= 2` rows with reasons; below it: Statistics, New Reports, Reused References, Unprocessed (`PENDING_KILLED`, silently retried next scan, `fail_count` untouched).

## yt-dlp maintenance

No auto-upgrade. Every 1–2 months run `pip install -U yt-dlp`, verify with one small playlist end-to-end, then pin the working version into `requirements.txt`. If downloads break, first step is always `yt-dlp --version` (expect drift, not a code bug).

## Architecture (only what's non-obvious)

- `src/pipeline.py:ProcessingPipeline` — download→transcribe→summarize→upload orchestrator; `run_youtube` / `run_local_mp3`; zero writes to the legacy DB. Accepts a shared `Transcriber` so batches pre-warm Whisper once (`src/batch.py:_make_shared_transcriber`).
- `src/channel_watcher.py:execute_scan` — TXT → `dateafter` fetch → one batched dedup-DB status query → `select_scan_videos` (newest-first, stop at first COMPLETED / old / dateless entry; FAILED listed, never auto-rerun) → oldest-first pipeline runs → Digest. `--max-hours` marks pending as `PENDING_KILLED`, Digest still emits.
- `src/summarizer.py` — transcripts truncated at `MAX_TRANSCRIPT_CHARS = 60000` (tail dropped, warning logged; no chunking by design). Waterfall: 429/5xx retried 3x per model, other non-auth errors switch model, 401/403 aborts immediately; total failure raises `RuntimeError("All OpenRouter models failed: ...")`.
- `src/run_tracker.py` — all dedup-DB access (`find_completed_video`, `mark_video_completed/failed/pending_killed`, `migrate_legacy_db`); `DatabaseManager` (`src/database.py`) for all SQLite (WAL, raises `DatabaseError`).
- Prompts: `src/prompt_selector.py` + `config/prompt_profile_map.csv` + `config/prompt_types/*.txt`. GitHub path: `summary/<first-letter>/<uploader>/YYYY_MM/file`. Output dirs: `output/transcripts/*.srt`, `output/summaries/`, `output/summary/` (`REPORT_DIR`).
- Exceptions: `PipelineError` subclasses in `src/exceptions.py`. Logging: `logger = logging.getLogger(__name__)`; console output via `src/cli/display.py`.

## Testing

```bash
python -m unittest discover tests   # 84 tests, must stay green
python -m unittest tests.test_dedup # single module
```

- `tests/test_*.py`, `test_<behavior>` methods, `unittest` only. No real network/API calls in tests (mock `requests.post` / fake pipelines).
- No `venv/bin/uvicorn`, no dashboard tests — both deleted with the dashboard.
