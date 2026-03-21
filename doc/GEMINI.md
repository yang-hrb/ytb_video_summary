# GEMINI.md - YouTube & Podcast Summarizer Context

This project is a Python-based automation tool designed to transcribe and summarize content from YouTube videos, Apple Podcasts, and local MP3 files using AI.

## Project Overview
- **Purpose**: Automatically convert audio/video content into structured Markdown summaries and SRT transcripts.
- **Core Technologies**:
  - **Transcription**: [OpenAI Whisper](https://github.com/openai/whisper) for high-accuracy speech-to-text.
  - **Summarization**: [OpenRouter](https://openrouter.ai/) (configurable via `.env`).
  - **Media Downloading**: [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube and custom RSS parsing for Apple Podcasts.
  - **Infrastructure**: Python 3.9+, FFmpeg for audio processing.
- **Key Features**: Supports single videos, playlists, podcasts, local folders, batch processing, and automated GitHub uploads of reports.

## Architecture
The project follows a modular design with clear separation of concerns:
- `src/main.py`: Entry point and CLI orchestrator.
- `src/transcriber.py`: Manages Whisper model loading and transcription logic.
- `src/summarizer.py`: Handles LLM prompt engineering and API interactions with waterfall fallback.
- `src/youtube_handler.py` & `src/apple_podcasts_handler.py`: Source-specific downloaders.
- `src/github_handler.py`: Manages automated uploads of reports and logs to a specified GitHub repository.
- `config/settings.py`: Centralized configuration management using `python-dotenv`.
- `src/logger.py`: Structured logging system with dual output (console and file).

## Directory Structure
- `src/`: Core logic and handlers.
- `config/`: Configuration and environment settings.
- `bash/`: Helper scripts for common tasks (`quick-run.sh`, `batch-run.sh`, etc.).
- `output/`:
  - `transcripts/`: Raw SRT subtitle files.
  - `summaries/`: Markdown summaries indexed by content ID.
  - `reports/`: Final timestamped reports (formatted for reading/sharing).
- `logs/`: Session-specific logs for debugging and auditing.
- `tests/`: Unit tests for core components.

## Building and Running

### Setup
1. **Prerequisites**: Ensure FFmpeg is installed (`brew install ffmpeg` on macOS).
2. **Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```
3. **Configuration**: Copy `.env.example` to `.env` and provide your `OPENROUTER_API_KEY`.

### Running
- **Single YouTube Video**: `python src/main.py -video "URL"`
- **YouTube Playlist**: `python src/main.py -list "URL"`
- **Apple Podcast**: `python src/main.py --apple-podcast-single "URL"`
- **Local MP3 Folder**: `python src/main.py -local "/path/to/folder"`
- **Batch Processing**: `python src/main.py --batch input.txt`
- **Helper Scripts**: Use `./quick-run.sh` for an interactive guided experience.

### Testing
```bash
python -m unittest discover tests
```

## Development Conventions
- **Configuration**: Always use `config.settings` instead of direct `os.getenv` calls to ensure validation and directory creation.
- **Logging**: Use the centralized logger (`logger.info`, `logger.error`, etc.) instead of `print()` for better traceability.
- **Error Handling**: Follow the pattern in `src/main.py` where failures are logged to `src/run_tracker.py` for potential resumption.
- **File Management**: Temporary files should be handled via `config.TEMP_DIR` and cleaned up after processing unless `--keep-audio` is specified.
- **Summaries**: Summaries support two styles (`brief` and `detailed`) and two languages (`zh` and `en`), controlled via CLI flags or `.env`.
