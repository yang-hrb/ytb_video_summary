#!/bin/bash
# YouTube Video Transcription & Summarization Tool Runner

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found!${NC}"
    echo "Please run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo -e "${CYAN}Activating virtual environment...${NC}"
source venv/bin/activate

# Check if activation was successful
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to activate virtual environment${NC}"
    exit 1
fi

echo -e "${GREEN}Virtual environment activated!${NC}"
echo ""

# Prompt for URL
echo -e "${YELLOW}Please paste the YouTube video URL (without quotes):${NC}"
read -r VIDEO_URL

# Check if URL is empty
if [ -z "$VIDEO_URL" ]; then
    echo -e "${RED}Error: No URL provided!${NC}"
    exit 1
fi

# Ask for optional parameters
echo ""
echo -e "${CYAN}Optional settings (press Enter to skip):${NC}"

# Summary style
echo -e "${YELLOW}Summary style (brief/detailed) [default: detailed]:${NC}"
read -r STYLE
if [ -z "$STYLE" ]; then
    STYLE="detailed"
fi

# Keep audio
echo -e "${YELLOW}Keep audio file after processing? (yes/no) [default: no]:${NC}"
read -r KEEP_AUDIO

# Cookies file
echo -e "${YELLOW}Cookies file path (for membership videos, press Enter to skip):${NC}"
read -r COOKIES_FILE

echo ""
echo -e "${GREEN}Starting video processing...${NC}"
echo ""

# Build command
CMD="python src/main.py \"$VIDEO_URL\" --style $STYLE"

if [ "$KEEP_AUDIO" = "yes" ] || [ "$KEEP_AUDIO" = "y" ]; then
    CMD="$CMD --keep-audio"
fi

if [ ! -z "$COOKIES_FILE" ]; then
    CMD="$CMD --cookies \"$COOKIES_FILE\""
fi

# Run the command
eval $CMD

# Check exit status
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Processing completed successfully!${NC}"
else
    echo ""
    echo -e "${RED}✗ Processing failed. Check the error messages above.${NC}"
    exit 1
fi
