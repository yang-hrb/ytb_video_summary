#!/bin/bash
# watch-run.sh - Run YouTube channel watcher

# Setup environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR" || exit 1

if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Pass arguments directly to main.py
python src/main.py --watch-run-once "$@"
