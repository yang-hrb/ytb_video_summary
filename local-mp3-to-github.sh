#!/bin/bash

# Local MP3 Processor with GitHub Upload
# This script processes local MP3 files and optionally uploads reports to GitHub

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
    echo -e "${CYAN}║   Local MP3 → GitHub Uploader                            ║${NC}"
    echo -e "${CYAN}║   Process local audio files and upload to GitHub         ║${NC}"
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

# Get MP3 folder path
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 1: MP3 Folder Path${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -z "$1" ]; then
    echo -e "${CYAN}Enter path to MP3 folder:${NC}"
    read folder_path
else
    folder_path="$1"
    print_info "Using provided path: $folder_path"
fi

# Validate folder path
if [ ! -d "$folder_path" ]; then
    print_error "Folder does not exist: $folder_path"
    exit 1
fi

# Check if folder contains MP3 files
mp3_count=$(find "$folder_path" -maxdepth 1 -name "*.mp3" -type f | wc -l)

if [ "$mp3_count" -eq 0 ]; then
    print_error "No MP3 files found in: $folder_path"
    exit 1
fi

echo ""
print_success "Found $mp3_count MP3 file(s) in folder"
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

# Process MP3 files
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 3: Processing MP3 Files${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
print_info "Starting MP3 file processing..."
echo ""

# Run the main program
python src/main.py -local "$folder_path" --style "$style"

exit_code=$?

echo ""

if [ $exit_code -eq 0 ]; then
    print_success "MP3 processing completed successfully!"
    echo ""

    # Ask about GitHub upload
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Step 4: Upload to GitHub${NC}"
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
    print_error "MP3 processing failed!"
    print_info "Check the log file for details: youtube_summarizer.log"
    exit 1
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
print_success "All done!"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
