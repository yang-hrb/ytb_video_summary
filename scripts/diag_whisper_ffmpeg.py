#!/usr/bin/env python3
"""Test Whisper with FFmpeg PATH fix"""

import sys
import os
from pathlib import Path

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils import find_ffmpeg_location

print("Testing Whisper FFmpeg PATH setup...")
print(f"Current PATH: {os.environ.get('PATH', 'Not set')[:100]}...")

ffmpeg_location = find_ffmpeg_location()
print(f"\nFFmpeg location detected: {ffmpeg_location}")

if ffmpeg_location:
    if ffmpeg_location not in os.environ.get('PATH', ''):
        os.environ['PATH'] = f"{ffmpeg_location}{os.pathsep}{os.environ.get('PATH', '')}"
        print(f"✓ Added FFmpeg to PATH: {ffmpeg_location}")
    else:
        print(f"✓ FFmpeg already in PATH")

    print(f"\nUpdated PATH (first 200 chars): {os.environ['PATH'][:200]}...")

    # Test if ffmpeg is now accessible
    import shutil
    ffmpeg = shutil.which('ffmpeg')
    if ffmpeg:
        print(f"✓ FFmpeg is now accessible: {ffmpeg}")
    else:
        print("✗ FFmpeg still not accessible in PATH")
else:
    print("✗ FFmpeg not found")
