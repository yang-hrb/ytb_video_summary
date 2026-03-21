import os
import platform
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    # OpenRouter API
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
    OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'openrouter/free')
    MODEL_PRIORITY_1 = os.getenv('MODEL_PRIORITY_1', 'openrouter/free')
    MODEL_PRIORITY_2 = os.getenv('MODEL_PRIORITY_2', 'openrouter/free')
    MODEL_PRIORITY_3 = os.getenv('MODEL_PRIORITY_3', 'openrouter/free')
    MODEL_FALLBACK = os.getenv('MODEL_FALLBACK', 'openrouter/free')

    # GitHub Integration
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
    GITHUB_REPO = os.getenv('GITHUB_REPO', '')
    GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'main')

    # Whisper
    WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'base')
    WHISPER_LANGUAGE = os.getenv('WHISPER_LANGUAGE', 'auto')
    WHISPER_BACKEND = os.getenv('WHISPER_BACKEND', 'auto')

    @staticmethod
    def resolve_whisper_backend() -> str:
        backend = Config.WHISPER_BACKEND.lower().strip()
        if backend == 'auto':
            if platform.system() == 'Darwin' and platform.machine() == 'arm64':
                return 'mlx'
            return 'openai'
        return backend if backend in ('mlx', 'openai') else 'openai'

    # Audio
    AUDIO_QUALITY = os.getenv('AUDIO_QUALITY', '64')
    AUDIO_FORMAT = os.getenv('AUDIO_FORMAT', 'mp3')
    KEEP_AUDIO = os.getenv('KEEP_AUDIO', 'false').lower() == 'true'

    # Summary
    SUMMARY_LANGUAGE = os.getenv('SUMMARY_LANGUAGE', 'zh')

    # Browser
    BROWSER_TYPE = os.getenv('BROWSER_TYPE', 'chrome')
    USE_COOKIES_FILE = os.getenv('USE_COOKIES_FILE', 'false').lower() == 'true'

    # HTTP/Network
    HTTP_USER_AGENT = os.getenv(
        'HTTP_USER_AGENT',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )
    HTTP_TIMEOUT = int(os.getenv('HTTP_TIMEOUT', '30'))
    HTTP_MAX_RETRIES = int(os.getenv('HTTP_MAX_RETRIES', '10'))

    # YouTube
    YOUTUBE_SLEEP_INTERVAL = int(os.getenv('YOUTUBE_SLEEP_INTERVAL', '3'))
    YOUTUBE_MAX_SLEEP = int(os.getenv('YOUTUBE_MAX_SLEEP', '6'))
    YOUTUBE_CONCURRENT_DOWNLOADS = int(os.getenv('YOUTUBE_CONCURRENT_DOWNLOADS', '1'))
    YOUTUBE_FRAGMENT_RETRIES = int(os.getenv('YOUTUBE_FRAGMENT_RETRIES', '10'))

    # Paths
    BASE_DIR = Path(__file__).parent.parent
    OUTPUT_DIR = BASE_DIR / os.getenv('OUTPUT_DIR', 'output')
    TEMP_DIR = BASE_DIR / os.getenv('TEMP_DIR', 'temp')
    LOG_DIR = BASE_DIR / 'logs'
    TRANSCRIPT_DIR = OUTPUT_DIR / 'transcripts'
    SUMMARY_DIR = OUTPUT_DIR / 'summaries'
    REPORT_DIR = OUTPUT_DIR / 'summary'

    @classmethod
    def validate(cls) -> bool:
        if not cls.OPENROUTER_API_KEY:
            raise ValueError("Set OPENROUTER_API_KEY in .env file")
        if cls.HTTP_TIMEOUT < 1:
            raise ValueError("HTTP_TIMEOUT must be positive")
        if cls.YOUTUBE_SLEEP_INTERVAL < 0:
            raise ValueError("YOUTUBE_SLEEP_INTERVAL must be non-negative")
        return True

    def __init__(self):
        self._create_directories()

    def _create_directories(self):
        for dir_path in [self.OUTPUT_DIR, self.TEMP_DIR, self.LOG_DIR,
                         self.TRANSCRIPT_DIR, self.SUMMARY_DIR, self.REPORT_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)


config = Config()
