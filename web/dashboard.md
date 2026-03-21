# Dashboard User Guide

## Overview
The Dashboard UI provides a graphical interface for the YTB Video Summary automation pipeline. Features include processing statistics, status tracking for recent runs, and a form to submit playlist/video URLs for processing.

## How to use
1. **Submit New Job**: Paste a YouTube/Podcast URL in the "Playlist/Video URL" field and click **Start Processing**. A job ID will be provided. In the background, the pipeline processes the playlist.
2. **View Stats**: The top section tracks Total, Completed, Failed, and Reused runs.
3. **Recent Runs**: You can find previously processed videos by searching their identifier or URL, or simply viewing the most recent events in the timeline table.

## Architecture
- **FastAPI**: Runs the web backend (`dashboard_app.py`, `dashboard_service.py`).
- **SQLite Tracker**: Reads off `run_track.db` which is populated by `main.py` and `run_tracker.py`.
- **Vanilla JS**: The dashboard itself runs on plain HTML/JS without extra bundler bloat, ensuring speed and reliability (`dashboard.html`).
