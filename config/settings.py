import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration class - Manages all environment variables and path settings"""

    # Summary API Configuration
    SUMMARY_API = os.getenv('SUMMARY_API', 'OPENROUTER').upper()  # OPENROUTER or PERPLEXITY

    # OpenRouter API
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
    OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'deepseek/deepseek-r1') # Model name to use, it may not be free!

    # Perplexity API
    PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY', '')
    PERPLEXITY_MODEL = os.getenv('PERPLEXITY_MODEL', 'sonar-pro')  # Perplexity model to use

    # GitHub Integration (optional)
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
    GITHUB_REPO = os.getenv('GITHUB_REPO', '')  # Format: owner/repo
    GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'main')

    # Whisper
    WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'base')
    WHISPER_LANGUAGE = os.getenv('WHISPER_LANGUAGE', 'zh')

    # Audio
    AUDIO_QUALITY = os.getenv('AUDIO_QUALITY', '64')
    AUDIO_FORMAT = os.getenv('AUDIO_FORMAT', 'mp3')
    KEEP_AUDIO = os.getenv('KEEP_AUDIO', 'false').lower() == 'true'

    # Summary Language (for AI-generated summaries and reports)
    # Options: 'en' for English, 'zh' for Chinese
    # Default: 'zh' (Chinese)
    # Note: Whisper transcription language is controlled by WHISPER_LANGUAGE
    SUMMARY_LANGUAGE = os.getenv('SUMMARY_LANGUAGE', 'zh')

    # Browser
    BROWSER_TYPE = os.getenv('BROWSER_TYPE', 'chrome')
    USE_COOKIES_FILE = os.getenv('USE_COOKIES_FILE', 'false').lower() == 'true'

    # Paths
    BASE_DIR = Path(__file__).parent.parent
    OUTPUT_DIR = BASE_DIR / os.getenv('OUTPUT_DIR', 'output')
    TEMP_DIR = BASE_DIR / os.getenv('TEMP_DIR', 'temp')
    LOG_DIR = BASE_DIR / 'logs'
    TRANSCRIPT_DIR = OUTPUT_DIR / 'transcripts'
    SUMMARY_DIR = OUTPUT_DIR / 'summaries'
    REPORT_DIR = OUTPUT_DIR / 'reports'

    def __init__(self):
        """Initialize and automatically create necessary directories"""
        self._create_directories()

    def _create_directories(self):
        """Create all necessary directories"""
        for dir_path in [self.OUTPUT_DIR, self.TEMP_DIR, self.LOG_DIR, self.TRANSCRIPT_DIR, self.SUMMARY_DIR, self.REPORT_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def validate(self):
        """Validate that required configuration is set"""
        if self.SUMMARY_API == 'OPENROUTER':
            if not self.OPENROUTER_API_KEY:
                raise ValueError("OPENROUTER_API_KEY is not set in .env file")
        elif self.SUMMARY_API == 'PERPLEXITY':
            if not self.PERPLEXITY_API_KEY:
                raise ValueError("PERPLEXITY_API_KEY is not set in .env file")
        else:
            raise ValueError(f"Invalid SUMMARY_API value: {self.SUMMARY_API}. Must be 'OPENROUTER' or 'PERPLEXITY'")
        return True

config = Config()
