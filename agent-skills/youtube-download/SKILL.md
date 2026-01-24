---
name: youtube-download
description: Download YouTube subtitles or MP3 audio and return video metadata. Use when a workflow needs to fetch YouTube content or inspect title/uploader/upload date/view/like counts before transcription.
---

# YouTube Download

Use this skill to fetch YouTube metadata and download subtitles (preferred) or MP3 audio when subtitles are unavailable.

## Environment setup

- Install FFmpeg on the host.
- Install Python dependencies:
  ```bash
  pip install -r requirements.txt
  ```
- Provide `cookies.txt` when accessing membership content.

## Inputs

- `--url`: YouTube video URL.
- `--cookies`: Optional path to `cookies.txt`.
- `--lang`: Subtitle language (default `zh`).
- `--output-dir`: Output directory (default `output/downloads`).

## Outputs

The script prints JSON with:
- `video_info`: title/uploader/upload_date/view_count/like_count, etc.
- `subtitle_path`: SRT path if subtitles were downloaded.
- `audio_path`: MP3 path if subtitles were not available.

## Run

```bash
python agent-skills/youtube-download/scripts/download_youtube.py \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --lang zh \
  --output-dir output/downloads
```

## Script

- `scripts/download_youtube.py`: Uses `src.youtube_handler.YouTubeHandler` to fetch metadata, download subtitles, or download MP3 audio.
