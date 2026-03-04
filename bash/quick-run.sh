#!/bin/bash
# Quick YouTube Video Transcription & Summarization
# Simple version - just paste URL and go!

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Activate virtual environment
echo -e "${CYAN}Loading...${NC}"
source venv/bin/activate

# Prompt for URL
echo -e "${YELLOW}Paste YouTube URL:${NC}"
read -r VIDEO_URL

if [ -z "$VIDEO_URL" ]; then
    echo "No URL provided!"
    exit 1
fi

echo -e "${GREEN}Processing video...${NC}"
echo ""

# Run with defaults
python src/main.py "$VIDEO_URL"
