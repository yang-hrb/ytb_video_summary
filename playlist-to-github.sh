#!/bin/bash

# YouTube Playlist Processor with GitHub Upload
# This script processes a YouTube playlist and optionally uploads reports to GitHub

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
    echo -e "${CYAN}║   YouTube Playlist → GitHub Uploader                     ║${NC}"
    echo -e "${CYAN}║   Process playlists and upload reports to GitHub         ║${NC}"
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

# Print header
print_header

# Check prerequisites
print_info "Checking prerequisites..."
check_venv
check_env
print_success "Prerequisites OK"
echo ""

# Activate virtual environment
print_info "Activating virtual environment..."
activate_venv
print_success "Virtual environment activated"
echo ""

# Get YouTube playlist URL
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 1: YouTube Playlist URL${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -z "$1" ]; then
    echo -e "${CYAN}Enter YouTube playlist URL:${NC}"
    read playlist_url
else
    playlist_url="$1"
    print_info "Using provided URL: $playlist_url"
fi

# Validate URL
if [[ ! "$playlist_url" =~ ^https?://(www\.)?(youtube\.com|youtu\.be) ]]; then
    print_error "Invalid YouTube URL!"
    exit 1
fi

echo ""
print_success "Playlist URL accepted"
echo ""

# Ask for summary style
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 2: Summary Style${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Choose summary style:"
echo "  1) Brief - Quick summary with key points"
echo "  2) Detailed - Comprehensive analysis (default)"
echo ""
echo -e "${CYAN}Enter choice [1-2]:${NC} "
read style_choice

case $style_choice in
    1)
        style="brief"
        print_info "Using brief summary style"
        ;;
    2|"")
        style="detailed"
        print_info "Using detailed summary style"
        ;;
    *)
        print_warning "Invalid choice, using detailed style"
        style="detailed"
        ;;
esac

echo ""

# Ask about cookies
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 3: Cookies (for membership videos)${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}Do you need to use cookies.txt? [y/N]:${NC} "
read use_cookies

cookies_param=""
if [[ "$use_cookies" =~ ^[Yy]$ ]]; then
    if [ -f "cookies.txt" ]; then
        cookies_param="--cookies cookies.txt"
        print_success "Will use cookies.txt"
    else
        print_error "cookies.txt not found!"
        print_info "Continuing without cookies..."
    fi
else
    print_info "Skipping cookies"
fi

echo ""

# Process playlist
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 4: Processing Playlist${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
print_info "Starting playlist processing..."
echo ""

# Run the main program
python src/main.py -list "$playlist_url" --style "$style" $cookies_param

exit_code=$?

echo ""

if [ $exit_code -eq 0 ]; then
    print_success "Playlist processing completed successfully!"
    echo ""

    # Ask about GitHub upload
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Step 5: Upload to GitHub${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Check if GitHub is configured
    if grep -q "^GITHUB_TOKEN=.\+$" .env && grep -q "^GITHUB_REPO=.\+$" .env; then
        echo -e "${CYAN}Upload reports to GitHub? [Y/n]:${NC} "
        read upload_choice

        if [[ ! "$upload_choice" =~ ^[Nn]$ ]]; then
            echo ""
            print_info "Uploading reports to GitHub..."
            echo ""

            python src/upload_to_github.py output/reports --skip-existing

            if [ $? -eq 0 ]; then
                echo ""
                print_success "Reports uploaded to GitHub successfully!"
            else
                echo ""
                print_error "GitHub upload failed!"
                print_info "Reports are saved locally in: output/reports/"
            fi
        else
            print_info "Skipping GitHub upload"
            print_info "Reports saved locally in: output/reports/"
        fi
    else
        print_warning "GitHub not configured in .env file"
        print_info "To enable GitHub upload, configure:"
        echo "  - GITHUB_TOKEN"
        echo "  - GITHUB_REPO"
        echo "  - GITHUB_BRANCH"
        print_info "Reports saved locally in: output/reports/"
    fi
else
    print_error "Playlist processing failed!"
    print_info "Check the log file for details: youtube_summarizer.log"
    exit 1
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
print_success "All done!"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
