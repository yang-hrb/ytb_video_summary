#!/bin/bash

# YouTube Playlist Summarizer - Docker Quick Run Script
# Usage: ./run-docker.sh "PLAYLIST_URL"

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║   YouTube Playlist Summarizer - Docker Runner            ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Print header
print_header

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed!"
    print_info "Install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found!"
    print_info "Copy .env.example to .env and configure it:"
    echo "  cp .env.example .env"
    exit 1
fi

# Get playlist URL
if [ -z "$1" ]; then
    echo -e "${YELLOW}Enter YouTube Playlist URL:${NC}"
    read playlist_url

    if [ -z "$playlist_url" ]; then
        print_error "No URL provided!"
        exit 1
    fi
else
    playlist_url="$1"
fi

# Validate URL
if [[ ! "$playlist_url" =~ ^https?://(www\.)?(youtube\.com|youtu\.be) ]]; then
    print_error "Invalid YouTube URL!"
    exit 1
fi

print_info "Playlist URL: $playlist_url"
echo ""

# Check if image exists, if not build it
if ! docker images | grep -q "ytb-playlist-summarizer"; then
    print_info "Docker image not found. Building..."
    docker build -t ytb-playlist-summarizer . || {
        print_error "Failed to build Docker image!"
        exit 1
    }
    print_success "Docker image built successfully"
    echo ""
fi

# Check for cookies file
cookies_param=""
if [ -f "cookies.txt" ]; then
    print_info "Found cookies.txt - will use for authentication"
    cookies_param="-v $(pwd)/cookies.txt:/app/cookies.txt:ro --cookies /app/cookies.txt"
fi

# Check for GitHub upload flag
upload_param=""
if grep -q "^GITHUB_TOKEN=.\+$" .env && grep -q "^GITHUB_REPO=.\+$" .env; then
    print_success "GitHub upload enabled"
    upload_param="--upload"
else
    print_warning "GitHub not configured - results will be saved locally only"
fi

echo ""
print_info "Starting Docker container..."
echo ""

# Create output directories if they don't exist
mkdir -p output/transcripts output/summaries output/reports logs

# Run Docker container
docker run --rm \
    --name ytb-summarizer-$(date +%s) \
    --env-file .env \
    -v "$(pwd)/output:/app/output" \
    -v "$(pwd)/logs:/app/logs" \
    ${cookies_param} \
    ytb-playlist-summarizer \
    -list "$playlist_url" \
    --style detailed \
    ${upload_param}

exit_code=$?

echo ""

if [ $exit_code -eq 0 ]; then
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    print_success "Processing completed successfully!"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    print_info "Output files location:"
    echo "  - Transcripts: output/transcripts/"
    echo "  - Summaries: output/summaries/"
    echo "  - Reports: output/reports/"
    echo "  - Logs: logs/"
else
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    print_error "Processing failed!"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    print_info "Check logs for details: logs/"
    exit 1
fi

echo ""
print_success "All done!"
echo ""
