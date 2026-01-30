# Repository Guidelines

## Project Structure & Module Organization
- `src/` contains the Python CLI and core pipeline (`main.py`, handlers, `transcriber.py`, `summarizer.py`).
- `config/` holds environment configuration (`settings.py`).
- `tests/` contains `unittest`-based test modules named `test_*.py`.
- `doc/` stores additional documentation (including a Chinese README).
- Generated artifacts live in `output/` (reports, summaries, transcripts), `logs/`, and `temp/`.
- Shell entrypoints live at the repo root (for example `quick-run.sh`, `batch-run.sh`, `full_auto_run_playlist.sh`).

## Build, Test, and Development Commands
- `python -m venv venv && source venv/bin/activate` to create/activate a virtualenv.
- `pip install -r requirements.txt` installs runtime dependencies.
- `cp .env.example .env` then set `OPENROUTER_API_KEY` or `PERPLEXITY_API_KEY`.
- `python src/main.py -video "URL"` runs the CLI directly.
- `./quick-run.sh` prompts for a URL and runs with defaults.
- `./batch-run.sh` processes `input.txt` batch files.
- `python -m unittest discover tests` runs the test suite.

## Coding Style & Naming Conventions
- Python uses 4-space indentation and standard PEP 8 conventions.
- Use `snake_case` for functions/variables and `PascalCase` for classes.
- Keep modules focused: handlers for external services, utilities in `src/utils.py`.
- There is no enforced formatter or linter; keep changes consistent with existing files.

## Testing Guidelines
- Tests use the standard library `unittest` framework.
- Name new tests `tests/test_<topic>.py` and test methods `test_<behavior>`.
- Run individual tests with `python -m unittest tests.test_transcriber`.

## Commit & Pull Request Guidelines
- Commit history favors short, imperative subjects with optional prefixes like `feat:`, `docs:`, or `refactor:`.
- Keep commits scoped to a single change and describe user-visible impact.
- PRs should include a concise summary, the commands used to test (if any), and screenshots or sample output when UI/report changes are involved.

## Security & Configuration Tips
- Never commit `.env` or API keys; use `.env.example` as the template.
- Generated files in `output/`, `logs/`, and `temp/` are local artifacts and should stay out of version control.
