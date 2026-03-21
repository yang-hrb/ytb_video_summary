# scripts/ — Diagnostic & Utility Scripts

This directory contains diagnostic and one-off utility scripts that are **NOT unit tests**.
They cannot be discovered by `python -m unittest discover tests` because they do not subclass
`unittest.TestCase`, and some make real API or system calls.

| Script | Purpose |
|--------|---------|
| `diag_api_key.py` | Verify the OpenRouter API key is valid (makes a real API call) |
| `diag_ffmpeg.py` | Check that FFmpeg is installed and accessible |
| `diag_whisper_ffmpeg.py` | Verify Whisper + FFmpeg integration works |

## Usage

Run from the project root with the virtual environment activated:

```bash
source venv/bin/activate
python scripts/diag_api_key.py
python scripts/diag_ffmpeg.py
python scripts/diag_whisper_ffmpeg.py
```
