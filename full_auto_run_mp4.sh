#!/bin/bash

# Full Auto Local MP4 Processor with GitHub Upload
# This script processes local MP4 files and automatically uploads reports to GitHub
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
    echo -e "${CYAN}║   Full Auto Local MP4 → GitHub Processor                 ║${NC}"
    echo -e "${CYAN}║   No confirmations - just provide path and go!           ║${NC}"
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

# Get folder path (from argument or prompt)
if [ -z "$1" ]; then
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Enter MP4 Folder Path${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${CYAN}Enter path to MP4 folder:${NC}"
    read folder_path

    if [ -z "$folder_path" ]; then
        echo ""
        print_error "No path provided!"
        exit 1
    fi
    echo ""
else
    folder_path="$1"
fi

# Validate folder path
if [ ! -d "$folder_path" ]; then
    print_error "Folder does not exist: $folder_path"
    exit 1
fi

# Check if folder contains MP4 files
mp4_count=$(find "$folder_path" -maxdepth 1 -name "*.mp4" -type f | wc -l)

if [ "$mp4_count" -eq 0 ]; then
    print_error "No MP4 files found in: $folder_path"
    exit 1
fi

print_info "MP4 folder: $folder_path"
print_info "Found $mp4_count MP4 file(s)"
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
echo "  Files to process: $mp4_count MP4 files"
echo "  Summary style: detailed (default)"
echo "  GitHub upload: $([ "$github_enabled" = true ] && echo 'enabled' || echo 'disabled')"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Build command parameters
upload_param=""
if [ "$github_enabled" = true ]; then
    upload_param="--upload"
fi

# Start processing
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Starting MP4 Processing${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Run the main program with --upload flag if GitHub is configured
python src/main.py --mp4-folder "$folder_path" --style detailed $upload_param

exit_code=$?

echo ""

if [ $exit_code -eq 0 ]; then
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    print_success "MP4 processing completed successfully!"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if [ "$github_enabled" = true ]; then
        print_info "Reports have been uploaded to GitHub automatically"
    else
        print_info "Reports are saved locally in: output/reports/"
    fi
else
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    print_error "MP4 processing failed!"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    print_info "Check the log file for details: youtube_summarizer.log"
    exit 1
fi

echo ""
print_success "All done!"
echo ""
