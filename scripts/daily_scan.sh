#!/bin/bash
# daily_scan.sh — 每天 04:00 全自动：扫 channellist.txt → 跑 pipeline → 发 Digest → 传 GitHub。
# 无新依赖：venv + .env + 防重叠（Python 侧 logs/scan.lock，stdlib Path）。
#
# crontab（每天 04:00；按实际路径替换）：
#   0 4 * * * /Users/yangyu/github/ytb_video_summary-Sep/scripts/daily_scan.sh >> /Users/yangyu/github/ytb_video_summary-Sep/logs/cron.log 2>&1
#
# 手动试跑：
#   ./scripts/daily_scan.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR" || exit 1

if [ -d "venv" ]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
fi

# .env 供 OPENROUTER_API_KEY / GITHUB_TOKEN / GITHUB_REPO（config 经 load_dotenv 也会读；此处显式导出方便排障）
if [ -f ".env" ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

COOKIES_PARAM=""
if [ -f "cookies.txt" ]; then
    COOKIES_PARAM="--cookies cookies.txt"
fi

# 对齐默认：detailed + cookies + upload；4 小时代码内计时停（半成品 Digest 照发）
# shellcheck disable=SC2086
python src/main.py --scan channellist.txt --style detailed $COOKIES_PARAM --upload --max-hours 4
