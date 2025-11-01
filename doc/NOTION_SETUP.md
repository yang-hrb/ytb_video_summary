# Notion Integration Setup Guide

This guide explains how to set up Notion integration for automatically saving video summaries to your Notion workspace.

## Overview

When enabled, the tool will automatically create a new page in your Notion database for each processed video, containing:
- Video title
- Content summary with AI-generated insights
- Video URL
- Uploader information
- Duration

## Setup Steps

### 1. Create a Notion Integration

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Click "New integration"
3. Give it a name (e.g., "YouTube Summarizer")
4. Select the workspace where you want to save summaries
5. Click "Submit"
6. Copy the "Internal Integration Token" - this is your `NOTION_API_KEY`

### 2. Create a Notion Database

1. In Notion, create a new page
2. Add a database (Table or Gallery view works well)
3. Configure the database with these properties:

   **Required Properties:**
   - `Name` (Title) - Will store the video title

   **Optional but Recommended Properties:**
   - `URL` (URL) - Video link
   - `Uploader` (Text) - Channel name
   - `Duration` (Text) - Video length

4. Share the database with your integration:
   - Click "..." in the top-right of the database
   - Click "Add connections"
   - Select your integration

5. Get the Database ID:
   - Open the database as a full page
   - Copy the URL, which looks like:
     ```
     https://www.notion.so/workspace/DATABASE_ID?v=...
     ```
   - The `DATABASE_ID` is the 32-character string (with hyphens removed, it's exactly 32 characters)
   - Example: `12345678901234567890123456789012`

### 3. Configure Environment Variables

Edit your `.env` file and add:

```bash
# Notion Configuration
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_DATABASE_ID=12345678901234567890123456789012
```

**Important:**
- `NOTION_API_KEY` starts with `secret_`
- `NOTION_DATABASE_ID` is exactly 32 characters (no hyphens)

### 4. Verify Setup

Run the tool with a test video:

```bash
python src/main.py "https://youtube.com/watch?v=test_video_id"
```

If successful, you should see:
```
Notion 页面:
  https://www.notion.so/...
```

## Optional: Disable Notion Integration

To disable Notion integration while keeping your configuration:

1. Simply remove or comment out the Notion variables in `.env`:
   ```bash
   # NOTION_API_KEY=...
   # NOTION_DATABASE_ID=...
   ```

2. Or leave them empty:
   ```bash
   NOTION_API_KEY=
   NOTION_DATABASE_ID=
   ```

The tool will automatically detect that Notion is not configured and skip the integration.

## Troubleshooting

### "Notion integration is disabled"
- Check that both `NOTION_API_KEY` and `NOTION_DATABASE_ID` are set in `.env`
- Verify the values are correct (no extra spaces)

### "Failed to create Notion page: 401"
- Your integration token is invalid or expired
- Create a new integration and update `NOTION_API_KEY`

### "Failed to create Notion page: 404"
- The database ID is incorrect
- Make sure you shared the database with your integration

### "Failed to create Notion page: 400"
- The database properties don't match what the integration expects
- Ensure your database has at least a "Name" (Title) property
- Optional properties (URL, Uploader, Duration) will be added only if they exist

## Advanced Configuration

### Custom Database Schema

You can customize the database properties. The integration will attempt to populate:

- **Name** (required): Video title
- **URL**: Video link (if property exists)
- **Uploader**: Channel name (if property exists)
- **Duration**: Video duration (if property exists)

Additional properties in your database will be ignored and can be filled manually.

### Content Formatting

The tool converts Markdown to Notion blocks:
- `#` Headers → Notion headings
- `-` Lists → Notion bullet lists
- `---` → Notion dividers
- Regular text → Notion paragraphs

## Benefits

✅ **Centralized knowledge base** - All video summaries in one place
✅ **Searchable** - Use Notion's powerful search
✅ **Organized** - Filter and sort by uploader, duration, date
✅ **Collaborative** - Share with team members
✅ **Cross-platform** - Access on web, desktop, and mobile
