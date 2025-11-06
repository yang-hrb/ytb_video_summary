#!/bin/bash

# Batch Processing Script for Audio/Video Transcription & Summarization Tool
# This script processes multiple inputs from a batch file

# Check if running in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Virtual environment not activated. Activating..."
    source venv/bin/activate
fi

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║   Batch Processing - Audio/Video Summarization Tool      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Prompt for batch file path
read -p "Enter batch input file path (default: input.txt): " BATCH_FILE
BATCH_FILE=${BATCH_FILE:-input.txt}

# Prompt for summary style
echo ""
echo "Summary style options:"
echo "  1) brief"
echo "  2) detailed (recommended)"
read -p "Enter choice (1 or 2, default: 2): " STYLE_CHOICE

if [ "$STYLE_CHOICE" = "1" ]; then
    STYLE="brief"
else
    STYLE="detailed"
fi

# Prompt for cookies file (for YouTube membership content)
echo ""
read -p "Use cookies.txt file? (y/n, default: n): " USE_COOKIES
if [ "$USE_COOKIES" = "y" ] || [ "$USE_COOKIES" = "Y" ]; then
    read -p "Enter cookies file path (default: cookies.txt): " COOKIES_FILE
    COOKIES_FILE=${COOKIES_FILE:-cookies.txt}
    COOKIES_ARG="--cookies $COOKIES_FILE"
else
    COOKIES_ARG=""
fi

# Prompt for audio retention (for YouTube videos)
echo ""
read -p "Keep downloaded audio files? (y/n, default: n): " KEEP_AUDIO
if [ "$KEEP_AUDIO" = "y" ] || [ "$KEEP_AUDIO" = "Y" ]; then
    KEEP_AUDIO_ARG="--keep-audio"
else
    KEEP_AUDIO_ARG=""
fi

# Prompt for GitHub upload
echo ""
read -p "Upload reports to GitHub? (y/n, default: n): " UPLOAD_GITHUB
if [ "$UPLOAD_GITHUB" = "y" ] || [ "$UPLOAD_GITHUB" = "Y" ]; then
    UPLOAD_ARG="--upload"
else
    UPLOAD_ARG=""
fi

# Run the program
echo ""
echo "Starting batch processing..."
echo "Batch file: $BATCH_FILE"
echo "Style: $STYLE"
echo ""

python src/main.py --batch "$BATCH_FILE" --style "$STYLE" $COOKIES_ARG $KEEP_AUDIO_ARG $UPLOAD_ARG

echo ""
echo "Batch processing complete!"
