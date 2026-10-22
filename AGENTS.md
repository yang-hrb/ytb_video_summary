# Repository Guide

This repository downloads or reads YouTube media, transcribes when needed, creates Markdown summaries, and can upload reports to GitHub. Podcast and dashboard features were removed in September 2026; keep future changes within the current CLI workflow.

## Entrypoints

Use the CLI examples below as the standard workflows. Full option details come from `python src/main.py --help`.

```bash
python src/main.py -video "https://youtube.com/watch?v=VIDEO_ID" --style detailed
python src/main.py -list "https://youtube.com/playlist?list=PLAYLIST_ID" --style detailed
python src/main.py -local ./audio_files --style detailed
python src/main.py --scan channellist.txt --style detailed --max-hours 4
```

`-local` expects a folder of MP3 files. `--scan` reads one channel URL per line; blank lines and `#` comments are ignored. Login-restricted videos can use `--cookies FILE`; browser cookies are opt-in. Add `--upload` only when a GitHub upload is intended. Use `--force` or `--no-reuse` to bypass completed-report reuse.

## Configuration

Install with `pip install -r requirements.txt`; FFmpeg is required for audio processing. Configuration is loaded from the repository-root `.env` by `config/settings.py`.

- `SUMMARY_PROVIDER` is `openrouter_free` by default or `agy_cli`. OpenRouter needs `OPENROUTER_API_KEY`; `agy_cli` needs an installed, authenticated `agy` executable.
- `GITHUB_TOKEN` and `GITHUB_REPO` are only needed for `--upload`.
- `WHISPER_BACKEND=auto` selects MLX on Apple Silicon and OpenAI Whisper elsewhere.
- OpenRouter summaries use at most 60,000 transcript characters. `agy_cli` receives the complete SRT.

See `.env.example` for supported settings.

## State and outputs

`logs/ytb_summary_track.db` is the only source of truth for completed-item reuse. It is initialized automatically and contains the `videos` table. A `COMPLETED` row is reused only when its `md_path` still exists; reuse skips download, transcription, summarization, and upload. `--force` bypasses this check.

YouTube IDs are the dedup keys for videos. Local MP3 IDs are `local_<sha256[:16]>`, computed from the first 8 MB plus file size; renaming a file does not change its key. Legacy `logs/run_track.db` data is migrated automatically to `logs/run_track_backup.db`; do not use either legacy database to determine current status.

The configured output paths are `output/transcripts/` (SRT), `output/summaries/` (intermediate summaries), and `output/summary/` (reports and daily digests). GitHub reports use `summary/<first-letter>/<uploader>/YYYY_MM/`.

## Channel scan behavior

`src/channel_watcher.py:execute_scan` reads the channel list, fetches videos from the last two days, selects eligible videos newest-first, then processes them oldest-first and generates a digest for the scan's start date. Completed, old, and dateless entries stop selection; failed entries are reported and are not automatically rerun by that scan.

`--max-hours` is an in-process time budget. Videos not dispatched before the deadline are marked `PENDING_KILLED` without increasing `fail_count`; a partial digest is still generated. `scripts/daily_scan.sh` runs this workflow with a four-hour budget and optional `cookies.txt`. The script does not install or schedule cron jobs.

`logs/two_time_fail.txt` records a video's second failure. The daily digest includes new reports, reused references, pending items, and failures with `fail_count >= 2`.

## Code map

- `src/cli/parser.py` and `src/cli/commands.py`: CLI options and dispatch.
- `src/pipeline.py`: one-video download/transcribe/summarize/upload orchestration and dedup reuse.
- `src/batch.py`: playlist, local-folder, and batch-file processing; shares a warmed Whisper transcriber across a batch.
- `src/run_tracker.py`: dedup database access, completion/failure records, and legacy migration.
- `src/database.py`: SQLite access through `DatabaseManager`.
- `src/summarizer.py`: provider selection, prompt application, and summary output.
- `src/prompt_selector.py`, `config/prompt_profile_map.csv`, `config/prompt_types/`: uploader-based prompt selection.
- `src/daily_summary.py`: Markdown daily digest generation.

## Development

Tests use `unittest` under `tests/test_*.py`. Run them with `python -m unittest discover tests`. Mock network and external-service calls; keep tests independent of real credentials and API calls.
