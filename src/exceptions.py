"""
项目特定异常层次结构

提供统一的异常类型，便于精确的错误处理和调试。
所有项目异常都继承自PipelineError基类。
"""

from typing import Optional


class PipelineError(Exception):
    """Pipeline处理异常的基类"""

    def __init__(self, message: str, stage: Optional[str] = None, original_error: Optional[Exception] = None):
        self.stage = stage
        self.original_error = original_error
        super().__init__(message)


class DownloadError(PipelineError):
    """下载失败异常

    用于YouTube视频下载、音频下载、字幕下载等场景。
    """
    pass


class TranscriptionError(PipelineError):
    """转录失败异常

    用于Whisper转录过程中的错误。
    """
    pass


class SummarizationError(PipelineError):
    """AI摘要生成失败异常

    用于OpenRouter API调用、模型降级等场景。
    """
    pass


class UploadError(PipelineError):
    """上传失败异常

    用于GitHub上传、文件存储等场景。
    """
    pass


class ConfigurationError(PipelineError):
    """配置错误异常

    用于缺少必要的环境变量、配置文件错误等场景。
    """
    pass


class PodcastError(PipelineError):
    """播客处理异常

    用于Apple Podcasts RSS解析、下载等场景。
    """
    pass


class DatabaseError(PipelineError):
    """数据库操作异常

    用于SQLite数据库操作失败场景。
    """
    pass


class ValidationError(PipelineError):
    """数据验证异常

    用于输入数据验证、URL格式验证等场景。
    """
    pass


class ExternalServiceError(PipelineError):
    """外部服务异常

    用于第三方API调用失败（如YouTube API、OpenRouter API等）。
    """

    def __init__(self, message: str, service_name: str, status_code: Optional[int] = None, **kwargs):
        self.service_name = service_name
        self.status_code = status_code
        super().__init__(message, **kwargs)
