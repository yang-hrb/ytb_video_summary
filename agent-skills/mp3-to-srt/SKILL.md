---
name: mp3-to-srt
description: Transcribe MP3 audio into SRT subtitles using Whisper. Use when an audio file exists and you need time-coded subtitles for summarization.
---

# MP3 to SRT

Use this skill to convert an MP3 audio file into SRT subtitles with Whisper.

## Environment setup

- Install FFmpeg on the host.
- Install Python dependencies:
  ```bash
  pip install -r requirements.txt
  ```
- Optionally set `.env` values: `WHISPER_MODEL`, `WHISPER_LANGUAGE`.

## Inputs

- `--mp3-path`: Path to the MP3 file.
- `--language`: `zh`, `en`, or `auto` (default `auto`).
- `--output-dir`: Output directory (default `output/transcripts`).

## Outputs

The script prints JSON with:
- `srt_path`: Path to the generated SRT file.
- `detected_language`: Whisper-detected language.

## Run

```bash
python agent-skills/mp3-to-srt/scripts/mp3_to_srt.py \
  --mp3-path output/downloads/VIDEO_ID.mp3 \
  --language auto \
  --output-dir output/transcripts
```

## Script

- `scripts/mp3_to_srt.py`: Uses `src.transcriber.Transcriber` to transcribe and write SRT output.
