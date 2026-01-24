---
name: srt-to-summary
description: Summarize SRT subtitles with OpenRouter free models and write a Markdown summary with reference metadata (author, title, upload date, likes, views). Use when subtitles are ready and you need a structured summary report.
---

# SRT to Summary

Use this skill to read SRT subtitles, call OpenRouter, and save a Markdown summary with a Reference section.

## Environment setup

- Set OpenRouter API key:
  ```bash
  export OPENROUTER_API_KEY=your_key
  ```
- Optionally set a free model:
  ```bash
  export OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free
  ```
- Install Python dependencies:
  ```bash
  pip install -r requirements.txt
  ```

## Inputs

- `--srt-path`: Path to the SRT file.
- `--youtube-url`: Optional URL for metadata (author/title/upload date/views/likes).
- `--language`: Summary language (`zh` or `en`, default `zh`).
- `--model`: Optional OpenRouter model override.
- `--output-dir`: Output directory (default `output/summaries`).
- `--cookies`: Optional cookies file for membership metadata.

## Outputs

The script prints JSON with:
- `summary_path`: Path to the generated Markdown file.
- `reference`: The Reference block written to the file.

## Run

```bash
python agent-skills/srt-to-summary/scripts/summarize_srt.py \
  --srt-path output/transcripts/VIDEO_ID.srt \
  --youtube-url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --language zh \
  --output-dir output/summaries
```

## Script

- `scripts/summarize_srt.py`: Reads SRT, builds prompt, calls OpenRouter, and writes summary Markdown.
