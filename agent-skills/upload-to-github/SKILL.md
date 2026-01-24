---
name: upload-to-github
description: Upload local Markdown files to a configured GitHub repository folder. Use when summaries are ready and need to be backed up or published to GitHub.
---

# Upload to GitHub

Use this skill to upload local Markdown files to a GitHub repository path.

## Environment setup

- Configure `.env` with GitHub settings:
  ```bash
  GITHUB_TOKEN=your_token
  GITHUB_REPO=owner/repo
  GITHUB_BRANCH=main
  ```
- Install Python dependencies:
  ```bash
  pip install -r requirements.txt
  ```

## Inputs

- `--local-dir`: Local directory containing `.md` files.
- `--remote-folder`: Target GitHub folder (default `reports`).
- `--skip-existing`: Skip files that already exist.

## Outputs

The script prints JSON upload stats:
- `total`, `success`, `failed`, `skipped`.

## Run

```bash
python agent-skills/upload-to-github/scripts/upload_markdown.py \
  --local-dir output/summaries \
  --remote-folder summaries
```

## Script

- `scripts/upload_markdown.py`: Wraps `src.upload_to_github` helpers to upload Markdown files.
