import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    """配置类 - 管理所有环境变量和路径设置"""

    # API Keys
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
    NOTION_API_KEY = os.getenv('NOTION_API_KEY', '')
    NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID', '')

    # Whisper
    WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'base')
    WHISPER_LANGUAGE = os.getenv('WHISPER_LANGUAGE', 'zh')

    # Audio
    AUDIO_QUALITY = os.getenv('AUDIO_QUALITY', '64')
    AUDIO_FORMAT = os.getenv('AUDIO_FORMAT', 'mp3')
    KEEP_AUDIO = os.getenv('KEEP_AUDIO', 'false').lower() == 'true'

    # Browser
    BROWSER_TYPE = os.getenv('BROWSER_TYPE', 'chrome')
    USE_COOKIES_FILE = os.getenv('USE_COOKIES_FILE', 'false').lower() == 'true'

    # Paths
    BASE_DIR = Path(__file__).parent.parent
    OUTPUT_DIR = BASE_DIR / os.getenv('OUTPUT_DIR', 'output')
    TEMP_DIR = BASE_DIR / os.getenv('TEMP_DIR', 'temp')
    TRANSCRIPT_DIR = OUTPUT_DIR / 'transcripts'
    SUMMARY_DIR = OUTPUT_DIR / 'summaries'
    REPORT_DIR = OUTPUT_DIR / 'reports'
    
    def __init__(self):
        """初始化时自动创建必要的目录"""
        self._create_directories()
    
    def _create_directories(self):
        """创建所有必要的目录"""
        for dir_path in [self.OUTPUT_DIR, self.TEMP_DIR, self.TRANSCRIPT_DIR, self.SUMMARY_DIR, self.REPORT_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def validate(self):
        """验证必要的配置是否已设置"""
        if not self.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is not set in .env file")
        return True

config = Config()
