#!/usr/bin/env python3
"""Test OpenRouter API key validity"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('OPENROUTER_API_KEY')

print(f"Testing API key: {api_key[:20]}..." if api_key else "No API key found")
print(f"API key starts with: {api_key[:10]}" if api_key else "")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://github.com/ytb_video_summary",
    "X-Title": "YouTube Video Summarizer"
}

payload = {
    "model": "deepseek/deepseek-r1",
    "messages": [
        {
            "role": "user",
            "content": "Say 'hello' in one word"
        }
    ],
    "max_tokens": 10
}

print("\nSending test request to OpenRouter API...")
print(f"URL: https://openrouter.ai/api/v1/chat/completions")
print(f"Headers: {headers}")

try:
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30
    )

    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {response.text}")

    if response.status_code == 200:
        print("\n✓ API key is valid!")
        result = response.json()
        print(f"Model response: {result['choices'][0]['message']['content']}")
    else:
        print("\n✗ API key validation failed!")

except Exception as e:
    print(f"\n✗ Error: {e}")
