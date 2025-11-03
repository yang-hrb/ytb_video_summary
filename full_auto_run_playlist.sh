#!/bin/bash

# Full Auto YouTube Playlist Processor with GitHub Upload
# This script processes a YouTube playlist and automatically uploads reports to GitHub
# No user confirmations required - uses default settings

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print colored message
print_header() {
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║   Full Auto YouTube Playlist → GitHub Processor          ║${NC}"
    echo -e "${CYAN}║   No confirmations - just provide URL and go!            ║${NC}"
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

# Check if virtual environment exists
check_venv() {
    if [ ! -d "venv" ]; then
        print_error "Virtual environment not found!"
        print_info "Please run: python -m venv venv"
        exit 1
    fi
}

# Activate virtual environment
activate_venv() {
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi
}

# Check if .env file exists
check_env() {
    if [ ! -f ".env" ]; then
        print_error ".env file not found!"
        print_info "Please copy .env.example to .env and configure it"
        exit 1
    fi
}

# Check if GitHub is configured
check_github_config() {
    if ! grep -q "^GITHUB_TOKEN=.\+$" .env || ! grep -q "^GITHUB_REPO=.\+$" .env; then
        print_warning "GitHub not configured in .env file"
        print_info "To enable GitHub upload, configure:"
        echo "  - GITHUB_TOKEN"
        echo "  - GITHUB_REPO"
        echo "  - GITHUB_BRANCH"
        echo ""
        print_info "Continuing without GitHub upload..."
        return 1
    fi
    return 0
}

# Print header
print_header

# Get playlist URL (from argument or prompt)
if [ -z "$1" ]; then
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Enter YouTube Playlist URL${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${CYAN}Paste your YouTube playlist URL:${NC}"
    read playlist_url

    if [ -z "$playlist_url" ]; then
        echo ""
        print_error "No URL provided!"
        exit 1
    fi
    echo ""
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

# Check prerequisites
print_info "Checking prerequisites..."
check_venv
check_env
print_success "Prerequisites OK"
echo ""

# Check GitHub configuration
github_enabled=false
if check_github_config; then
    github_enabled=true
    print_success "GitHub upload enabled"
else
    print_info "Reports will be saved locally only"
fi
echo ""

# Activate virtual environment
print_info "Activating virtual environment..."
activate_venv
print_success "Virtual environment activated"
echo ""

# Display processing settings
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Processing Settings${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "  Summary style: detailed (default)"
echo "  GitHub upload: $([ "$github_enabled" = true ] && echo 'enabled' || echo 'disabled')"
echo "  Cookies: auto-detect if available"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check for cookies file
cookies_param=""
if [ -f "cookies.txt" ]; then
    print_info "Found cookies.txt - will use for authentication"
    cookies_param="--cookies cookies.txt"
fi
echo ""

# Build command parameters
upload_param=""
if [ "$github_enabled" = true ]; then
    upload_param="--upload"
fi

# Start processing
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Starting Playlist Processing${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Run the main program with --upload flag if GitHub is configured
python src/main.py -list "$playlist_url" --style detailed $cookies_param $upload_param

exit_code=$?

echo ""

if [ $exit_code -eq 0 ]; then
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    print_success "Playlist processing completed successfully!"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if [ "$github_enabled" = true ]; then
        print_info "Reports have been uploaded to GitHub automatically"
    else
        print_info "Reports are saved locally in: output/reports/"
    fi
else
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    print_error "Playlist processing failed!"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    print_info "Check the log file for details: youtube_summarizer.log"
    exit 1
fi

echo ""
print_success "All done!"
echo ""
