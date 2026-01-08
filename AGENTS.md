# AGENTS.md

This file guides agentic coding agents working in this repository.

## Build/Test Commands

### Testing
```bash
# Run all tests
python -m unittest discover tests

# Run specific test module
python -m unittest tests.test_youtube
python -m unittest tests.test_transcriber
python -m unittest tests.test_summarizer
python -m unittest tests.test_api_key

# Run single test class
python -m unittest tests.test_summarizer.TestSummarizer

# Run single test method
python -m unittest tests.test_summarizer.TestSummarizer.test_create_prompt_brief
```

### Running the Application
```bash
# Quick mode (uses defaults)
./quick-run.sh

# Full mode with options
./run.sh

# Direct Python execution
python src/main.py "https://youtube.com/watch?v=xxxxx"
python src/main.py -list "https://youtube.com/playlist?list=xxxxx"
python src/main.py --apple-podcast-single "https://podcasts.apple.com/..."
python src/main.py -local /path/to/mp3/folder
python src/main.py --batch input.txt
```

### Environment Setup
```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
cp .env.example .env
# Edit .env to add API keys
```

## Code Style Guidelines

### File Organization
- `src/` - Main application code
- `config/` - Configuration management
- `tests/` - Unit tests (one test file per module)
- `doc/` - Documentation
- `logs/` - Runtime logs and tracking database

### Import Ordering
Standard library imports → Third-party imports → Local imports

```python
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

import requests
import logging

from config import config
from src.utils import sanitize_filename
from .utils import format_timestamp
```

### Naming Conventions
- **Classes**: `CamelCase` (e.g., `YouTubeHandler`, `Transcriber`, `Summarizer`)
- **Functions/Methods**: `snake_case` (e.g., `process_video`, `transcribe_audio`, `save_as_srt`)
- **Constants**: `UPPER_CASE` (e.g., `SUMMARY_API`, `WHISPER_MODEL`, `AUDIO_QUALITY`)
- **Variables**: `snake_case` (e.g., `video_id`, `audio_path`, `transcript`)
- **Private methods**: `_snake_case` (e.g., `_init_database`, `_summarize_openrouter`)

### Type Hints
Always include type hints for function parameters and return values:

```python
def process_video(
    url: str,
    cookies_file: Optional[str] = None,
    keep_audio: bool = False,
    summary_style: str = "detailed"
) -> dict:
    """Process a single video through the pipeline"""

def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """Remove illegal characters from filename"""
```

Use `Optional[T]` for nullable types, `Dict[K, V]`, `List[T]` from `typing` module.

### Docstrings
Use triple-quoted docstrings with Args and Returns sections:

```python
def get_video_info(self, url: str) -> Dict:
    """
    Get video information (without downloading)

    Args:
        url: YouTube video URL

    Returns:
        Dictionary containing video information (id, title, duration, uploader, etc.)
    """
```

### String Formatting
Use f-strings for string interpolation:

```python
logger.info(f"Processing video: {video_id}")
logger.info(f"  Title: {video_info['title']}")
logger.info(f"  Duration: {video_info['duration']}s")
```

### Error Handling
- Use try/except blocks for external operations
- Log errors with `logger.error()` or `logger.warning()`
- Re-raise exceptions after logging unless explicitly handling

```python
try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
except Exception as e:
    logger.error(f"Failed to get video info: {e}")
    raise
```

### Logging
Always log at appropriate levels:
- `logger.debug()` - Detailed debugging info
- `logger.info()` - General operational info
- `logger.warning()` - Warning messages (e.g., missing subtitles)
- `logger.error()` - Error messages with context

Get logger at module level: `logger = logging.getLogger(__name__)`

### Path Operations
Use `pathlib.Path` for all file system operations:

```python
from pathlib import Path

output_path = config.OUTPUT_DIR / f"{video_id}_summary.md"
audio_path.unlink()  # Delete file
if output_path.exists():
    content = output_path.read_text()
```

### Configuration Access
Access configuration via `config` singleton:

```python
from config import config

api_key = config.OPENROUTER_API_KEY
model = config.WHISPER_MODEL
output_dir = config.OUTPUT_DIR
```

### Class Design Patterns
- Use class-based handlers (e.g., `YouTubeHandler`, `Transcriber`, `Summarizer`)
- Lazy initialization for expensive resources (e.g., Whisper model loading)
- Provide both class methods and convenience functions

```python
class Transcriber:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or config.WHISPER_MODEL
        self.model = None

    def load_model(self):
        """Lazy-load Whisper model"""
        if self.model is None:
            self.model = whisper.load_model(self.model_name)

# Convenience function
def transcribe_video_audio(audio_path: Path, video_id: str) -> tuple:
    """Wrapper for common use case"""
```

### Return Values
Functions typically return:
- Dictionaries for structured data: `{'video_id': ..., 'info': ..., 'path': ...}`
- Tuples for simple multiple returns: `(transcript, language)`
- `None` or `Optional[Path]` for optional operations

### CLI Arguments
Use `argparse` for CLI with proper help text:

```python
parser.add_argument(
    '-video',
    type=str,
    metavar='URL',
    help='YouTube video URL'
)

parser.add_argument(
    '--style',
    choices=['brief', 'detailed'],
    default='detailed',
    help='Summary style: brief or detailed'
)
```

### File Encoding
Always specify UTF-8 encoding when reading/writing files:

```python
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(content)
```

### Module __init__.py
Keep minimal - just package metadata:

```python
"""YouTube Video Transcription & Summarization Tool"""

__version__ = '1.0.0'
```

### Testing Patterns
- Use `unittest.TestCase`
- Test methods start with `test_`
- Use descriptive test names in docstrings (Chinese or English)

```python
class TestSummarizer(unittest.TestCase):
    """测试总结器"""

    def test_create_prompt_brief(self):
        """测试简短风格提示词创建"""
        summarizer = Summarizer(api_key="test_key")
        prompt = summarizer.create_prompt("test", style="brief")
        self.assertIn("关键要点", prompt)
```

## Important Notes

### System Path Handling
Main.py ensures project root is in `sys.path`:

```python
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
```

### Run Tracking
Use `RunTracker` for all processing operations:

```python
from src.run_tracker import get_tracker, log_failure

tracker = get_tracker()
run_id = tracker.start_run('youtube', url, video_id)
tracker.update_status(run_id, 'working')
# ... process ...
tracker.update_status(run_id, 'done')

# Log failures
log_failure('youtube', video_id, url, str(e))
```

### Configuration Validation
Always validate config before processing:

```python
try:
    config.validate()
except ValueError as e:
    log_error(str(e))
    sys.exit(1)
```

### Language Configuration
- `WHISPER_LANGUAGE` - Controls transcription language (zh/en/auto)
- `SUMMARY_LANGUAGE` - Controls AI summary output language (zh/en)
- These are independent settings
