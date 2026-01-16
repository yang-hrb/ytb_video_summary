#!/bin/bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

if [ -f ".env" ]; then
  set -a
  source .env
  set +a
fi

if [ -z "${VIRTUAL_ENV:-}" ] && [ -d "venv" ]; then
  source venv/bin/activate
fi

python src/channel_cron.py --style detailed --upload
