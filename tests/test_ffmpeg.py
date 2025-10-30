#!/usr/bin/env python3
"""Test FFmpeg detection"""

import sys
from pathlib import Path

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils import find_ffmpeg_location

print("Testing FFmpeg auto-detection...")
location = find_ffmpeg_location()

if location:
    print(f"✓ FFmpeg found at: {location}")

    # Verify it's executable
    ffmpeg_path = Path(location) / "ffmpeg"
    if ffmpeg_path.exists():
        print(f"✓ FFmpeg executable confirmed: {ffmpeg_path}")
    else:
        print(f"⚠ FFmpeg directory found but executable not confirmed")
else:
    print("✗ FFmpeg not found")
    print("\nPlease install FFmpeg:")
    print("  macOS: brew install ffmpeg")
    print("  Ubuntu/Debian: sudo apt install ffmpeg")
    print("  Windows: Download from https://ffmpeg.org")
