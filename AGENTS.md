# Repository Guidelines

## Project Structure & Module Organization

```
.
├── src/                    # Core source code
│   ├── cli/                # CLI module (Phase 2)
│   │   ├── parser.py       # Argument parsing
│   │   ├── commands.py     # Command handling
│   │   └── display.py      # Console output
│   ├── main.py             # Entry point (~215 lines)
│   ├── pipeline.py         # Processing pipeline
│   ├── exceptions.py       # Exception hierarchy (Phase 1)
│   ├── database.py         # Database access layer (Phase 1)
│   ├── batch_processor.py  # Generic batch processor (Phase 2)
│   ├── run_tracker.py      # State tracking
│   ├── youtube_handler.py  # YouTube download
│   ├── apple_podcasts_handler.py  # Apple Podcasts
│   ├── transcriber.py      # Whisper transcription
│   ├── summarizer.py       # AI summarization
│   └── utils.py            # Utilities
├── config/                 # Environment configuration
│   ├── settings.py         # Centralized config (Phase 3)
│   ├── prompt_types/       # AI prompt templates
│   └── prompt_profile_map.csv  # Uploader-to-prompt mapping
├── tests/                  # unittest-based tests (40 tests)
├── scripts/                # Shell scripts and diagnostics
│   ├── quick-run.sh        # Quick single video processing
│   ├── batch-run.sh        # Batch file processing
│   ├── watch-run.sh        # Channel watcher daemon
│   ├── dashboard.sh        # Web dashboard launcher
│   ├── full_auto_run_*.sh  # Automated processing scripts
│   └── diagnostics/        # Diagnostic utilities
├── doc/                    # Documentation
├── web/                    # Web dashboard frontend
├── output/                 # Generated artifacts (gitignored)
├── logs/                   # Log files (gitignored)
└── temp/                   # Temporary files (gitignored)
```

## Build, Test, and Development Commands

```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then set OPENROUTER_API_KEY

# Run
python src/main.py -video "URL"
python src/main.py --help

# Web Dashboard
./scripts/dashboard.sh

# Test
python -m unittest discover tests

# Lint (optional)
mypy src/ --ignore-missing-imports
```

## Coding Style & Naming Conventions

- Python uses 4-space indentation and standard PEP 8 conventions
- Use `snake_case` for functions/variables and `PascalCase` for classes
- All public APIs should have type annotations (Phase 2)
- Use project-specific exceptions from `src/exceptions.py` (Phase 1)
- Use `DatabaseManager` for database operations (Phase 1)
- Use `BatchProcessor` for batch operations (Phase 2)
- Configuration values should be in `config/settings.py` (Phase 3)

## Architecture Decisions

### Phase 1: Stability
- **Exception Hierarchy**: All exceptions inherit from `PipelineError`
- **Database Layer**: Use `DatabaseManager` for unified DB access with WAL mode
- **Error Handling**: No empty except blocks; always log errors

### Phase 2: Code Quality
- **CLI Separation**: `src/cli/` handles all CLI logic
- **Type Annotations**: All public APIs have complete type hints
- **Batch Processing**: Use `BatchProcessor` for any batch operations

### Phase 3: Maintainability
- **Centralized Config**: All config in `config/settings.py` with validation
- **Console Output**: Use `src/cli/display.py` for user output
- **Testing**: Maintain test coverage for new modules

### Phase 4: Tooling
- **Scripts**: All shell scripts in `scripts/` directory
- **Diagnostics**: Diagnostic tools in `scripts/diagnostics/`
- **Documentation**: Architecture decisions in `doc/`

## Testing Guidelines

- Tests use the standard library `unittest` framework
- Name new tests `tests/test_<topic>.py` and test methods `test_<behavior>`
- Run individual tests with `python -m unittest tests.test_transcriber`
- Current test count: 40 tests (100% passing)

## Commit & Pull Request Guidelines

- Commit history favors short, imperative subjects with optional prefixes like `feat:`, `docs:`, or `refactor:`.
- Keep commits scoped to a single change and describe user-visible impact.
- PRs should include a concise summary, the commands used to test (if any), and screenshots or sample output when UI/report changes are involved.

## Security & Configuration Tips

- Never commit `.env` or API keys; use `.env.example` as the template.
- Generated files in `output/`, `logs/`, and `temp/` are local artifacts and should stay out of version control.
- Cookies files (`cookies.txt`) contain sensitive data and are gitignored.
