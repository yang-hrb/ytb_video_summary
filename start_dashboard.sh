#!/bin/bash

# Configuration
HOST="127.0.0.1"
PORT=8999

# Colors for output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}======================================================${NC}"
echo -e "${CYAN}   Starting YouTube Video Summarizer Dashboard        ${NC}"
echo -e "${CYAN}======================================================${NC}"
echo -e ""

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    echo -e "📦 Activating virtual environment..."
    source venv/bin/activate
else
    echo -e "⚠️  Warning: Virtual environment not found at venv/bin/activate."
    echo -e "   Falling back to system Python..."
fi

echo -e "🚀 Starting FastAPI server on port ${PORT}..."
echo -e "🌐 Access the Dashboard at: ${GREEN}http://${HOST}:${PORT}/dashboard${NC}"
echo -e "   Press [Ctrl+C] to stop the server."
echo -e ""

# Start uvicorn
uvicorn src.dashboard_app:app --host $HOST --port $PORT --reload
