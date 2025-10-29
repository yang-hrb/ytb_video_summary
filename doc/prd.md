# PRD - YouTube 视频转录与总结工具

## 📋 项目概述

**项目名称**: YouTube Transcript & Summarizer  
**版本**: v1.0  
**目标**: 自动将 YouTube 视频（包括会员视频）转录为文字并生成 AI 总结

### 核心功能
1. 支持 YouTube 普通视频和会员视频
2. 自动提取或生成字幕
3. AI 智能总结视频内容
4. 节省存储空间（可选删除音频）

---

## 🎯 功能需求

### 1. 视频下载
- [x] 支持 YouTube URL 输入
- [x] 自动提取视频元数据（标题、时长等）
- [x] 支持会员视频（通过浏览器 cookies）
- [x] 下载音频流（64kbps MP3，节省空间）

### 2. 字幕生成
- [x] 优先提取 YouTube 原生字幕（如果存在）
- [x] 使用 Whisper 生成字幕（无字幕时）
- [x] 支持中文、英文等多语言
- [x] 输出带时间戳的字幕文件（SRT/VTT）

### 3. AI 总结
- [x] 使用 OpenRouter 免费模型生成总结
- [x] 支持多种总结风格（简短/详细）
- [x] 提取关键要点
- [x] 生成时间轴摘要

### 4. 存储优化
- [x] 音频质量可配置（32/64/128 kbps）
- [x] 转录后自动删除音频（可选）
- [x] 仅保存文本结果

---

## 🛠 技术栈

### 核心技术
| 技术 | 用途 | 版本要求 |
|------|------|----------|
| **Python** | 主要开发语言 | 3.9+ |
| **yt-dlp** | YouTube 视频下载 | 最新版 |
| **OpenAI Whisper** | 语音转文字 | 最新版 |
| **OpenRouter API** | AI 文本总结 | - |
| **FFmpeg** | 音频处理 | 4.0+ |

### 推荐模型
- **Whisper**: `base` 模型（M2 Mac 推荐）
- **总结模型**: DeepSeek R1 / Gemini 2.5 Flash（免费）

### 开发环境
- **硬件**: Mac Mini M2（或同等性能设备）
- **系统**: macOS / Linux / Windows
- **浏览器**: Chrome / Firefox / Edge（用于 cookies）

---

## 📁 项目结构

```
youtube-summarizer/
├── README.md                 # 项目说明
├── PRD.md                   # 本文档
├── requirements.txt         # Python 依赖
├── .env.example            # 环境变量模板
├── .gitignore              # Git 忽略配置
│
├── config/
│   ├── __init__.py
│   └── settings.py         # 配置管理
│
├── src/
│   ├── __init__.py
│   ├── main.py             # 主入口
│   ├── youtube_handler.py  # YouTube 下载逻辑
│   ├── transcriber.py      # Whisper 转录逻辑
│   ├── summarizer.py       # AI 总结逻辑
│   └── utils.py            # 工具函数
│
├── output/                 # 输出目录
│   ├── transcripts/        # 字幕文件
│   └── summaries/          # 总结文件
│
├── temp/                   # 临时文件（音频）
│   └── .gitkeep
│
└── tests/                  # 单元测试
    ├── __init__.py
    ├── test_youtube.py
    ├── test_transcriber.py
    └── test_summarizer.py
```

---

## ⚙️ 配置说明

### 1. 环境变量 (`.env`)

```bash
# OpenRouter API
OPENROUTER_API_KEY=your_api_key_here

# Whisper 配置
WHISPER_MODEL=base  # tiny/base/small/medium/large
WHISPER_LANGUAGE=zh  # zh/en/auto

# 音频配置
AUDIO_QUALITY=64  # 32/64/96/128 kbps
AUDIO_FORMAT=mp3  # mp3/opus
KEEP_AUDIO=false  # true/false

# 浏览器配置（会员视频）
BROWSER_TYPE=chrome  # chrome/firefox/edge/safari
USE_COOKIES_FILE=false  # true 时使用 cookies.txt

# 输出配置
OUTPUT_DIR=output
TEMP_DIR=temp
```

### 2. 配置文件 (`config/settings.py`)

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
    
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
    
    # 自动创建目录
    for dir_path in [OUTPUT_DIR, TEMP_DIR, TRANSCRIPT_DIR, SUMMARY_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)

config = Config()
```

### 3. 依赖文件 (`requirements.txt`)

```txt
# Core
yt-dlp>=2024.10.0
openai-whisper>=20231117
python-dotenv>=1.0.0

# API
requests>=2.31.0
openai>=1.0.0  # For OpenRouter

# Audio Processing
ffmpeg-python>=0.2.0

# Utilities
tqdm>=4.66.0
colorama>=0.4.6

# Optional: 更快的 Whisper
# faster-whisper>=0.10.0
```

---

## 📝 实施步骤

### Phase 1: 环境搭建 (Day 1)

**1.1 安装系统依赖**
```bash
# Mac
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# 从 https://ffmpeg.org 下载
```

**1.2 创建 Python 环境**
```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

**1.3 配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，填入 API Key
```

### Phase 2: 核心功能开发 (Day 2-3)

**2.1 YouTube 下载模块**
- 实现 `youtube_handler.py`
- 支持普通视频下载
- 支持会员视频（cookies）
- 音频质量控制

**2.2 Whisper 转录模块**
- 实现 `transcriber.py`
- 检测原生字幕
- Whisper 转录（无字幕时）
- 输出 SRT 格式

**2.3 AI 总结模块**
- 实现 `summarizer.py`
- 集成 OpenRouter API
- 提示词优化
- 结构化输出

### Phase 3: 集成与优化 (Day 4)

**3.1 主程序集成**
- 实现 `main.py`
- 命令行参数解析
- 错误处理
- 进度显示

**3.2 存储优化**
- 临时文件清理
- 音频自动删除
- 输出目录管理

### Phase 4: 测试与文档 (Day 5)

**4.1 单元测试**
- 测试各模块功能
- 边界情况处理

**4.2 文档完善**
- README 使用说明
- 示例代码
- 故障排除

---

## ✅ 开发 Checklist

### 环境准备
- [ ] 安装 Python 3.9+
- [ ] 安装 FFmpeg
- [ ] 创建虚拟环境
- [ ] 安装项目依赖
- [ ] 配置 .env 文件
- [ ] 获取 OpenRouter API Key

### 模块开发
- [ ] 实现 `config/settings.py`
- [ ] 实现 `src/youtube_handler.py`
  - [ ] 普通视频下载
  - [ ] 会员视频支持（cookies）
  - [ ] 音频质量控制
  - [ ] 元数据提取
- [ ] 实现 `src/transcriber.py`
  - [ ] 检测原生字幕
  - [ ] Whisper 模型加载
  - [ ] 音频转录
  - [ ] SRT 文件生成
- [ ] 实现 `src/summarizer.py`
  - [ ] OpenRouter API 集成
  - [ ] 提示词设计
  - [ ] 结果解析
  - [ ] 错误处理
- [ ] 实现 `src/utils.py`
  - [ ] 文件管理
  - [ ] 日志记录
  - [ ] 时间格式化
- [ ] 实现 `src/main.py`
  - [ ] 命令行参数
  - [ ] 流程编排
  - [ ] 进度显示

### 功能测试
- [ ] 测试普通视频下载
- [ ] 测试会员视频下载
- [ ] 测试有字幕视频（跳过 Whisper）
- [ ] 测试无字幕视频（使用 Whisper）
- [ ] 测试中文视频
- [ ] 测试英文视频
- [ ] 测试 AI 总结输出
- [ ] 测试音频删除功能
- [ ] 测试错误处理

### 优化与完善
- [ ] 代码注释完善
- [ ] 添加类型提示
- [ ] 性能优化
- [ ] 内存使用优化
- [ ] 错误信息优化

### 文档与发布
- [ ] 编写 README.md
- [ ] 添加使用示例
- [ ] 编写故障排除指南
- [ ] 添加 LICENSE
- [ ] 创建 .gitignore
- [ ] 初始化 Git 仓库

---

## 🚀 快速开始示例

### 基础使用

```bash
# 处理单个视频
python src/main.py "https://youtube.com/watch?v=xxxxx"

# 指定输出格式
python src/main.py "URL" --format detailed

# 保留音频文件
python src/main.py "URL" --keep-audio

# 使用 cookies 文件（会员视频）
python src/main.py "URL" --cookies cookies.txt
```

### Python 调用

```python
from src.main import process_video

result = process_video(
    url="https://youtube.com/watch?v=xxxxx",
    keep_audio=False,
    summary_style="detailed"
)

print(result['summary'])
```

---

## 📊 预期输出

### 文件结构
```
output/
├── transcripts/
│   └── [video_id]_transcript.srt
└── summaries/
    └── [video_id]_summary.md
```

### 总结格式 (Markdown)

```markdown
# 视频标题

**时长**: 15:30  
**生成时间**: 2025-10-29 10:30:00

## 📝 内容摘要
[3-5 句话的核心内容总结]

## 🎯 关键要点
- 要点 1
- 要点 2
- 要点 3

## ⏱ 时间轴
- 00:00 - 开场介绍
- 02:30 - 主题 1
- 08:15 - 主题 2
- 13:45 - 总结

## 💡 核心见解
[深度分析和启发]
```

---

## ⚠️ 注意事项

### 安全与合规
- ⚠️ **不要**将 `cookies.txt` 提交到 Git
- ⚠️ **不要**分享或二次分发会员内容
- ⚠️ **仅用于**个人学习使用
- ⚠️ 遵守 YouTube 服务条款

### 性能建议
- M2 Mac 推荐使用 `base` 或 `small` Whisper 模型
- 长视频（>1小时）建议使用 `tiny` 或 `base` 模型
- 批量处理时注意 API 速率限制

### 故障排除
- **HTTP 403 错误**: 更新 yt-dlp (`pip install -U yt-dlp`)
- **Cookies 过期**: 重新导出浏览器 cookies
- **Whisper 慢**: 降低模型大小或使用 `faster-whisper`
- **API 限流**: 添加重试逻辑和延迟

---

## 🔮 未来扩展

### v2.0 计划
- [ ] 支持批量处理多个视频
- [ ] 添加 Web UI 界面
- [ ] 支持更多视频平台（Bilibili、Vimeo）
- [ ] 多语言翻译功能
- [ ] 导出 PDF/Word 格式
- [ ] 添加视频关键帧截图
- [ ] 集成更多 AI 模型选择

### v3.0 愿景
- [ ] 构建本地知识库
- [ ] 视频内容检索
- [ ] 跨视频内容关联
- [ ] 自动生成思维导图

---

## 📞 支持与反馈

- **问题报告**: GitHub Issues
- **功能建议**: GitHub Discussions
- **文档**: [待补充]

---

## 📄 License

MIT License

---

**最后更新**: 2025-10-29  
**维护者**: [Yang Yu]
