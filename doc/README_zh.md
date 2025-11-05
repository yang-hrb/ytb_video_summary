# YouTube 视频转录与总结工具

[English Documentation (英文文档)](../README.md)

🎥 自动将 YouTube 视频（包括会员视频）转录为文字并生成 AI 智能总结

## ✨ 特性

- ✅ 支持 YouTube 普通视频和会员视频
- ✅ 自动提取或生成字幕
- ✅ AI 智能总结视频内容（支持 OpenRouter 和 Perplexity API）
- ✅ **可配置总结 API** - 通过 `.env` 文件轻松切换 OpenRouter 和 Perplexity
- ✅ **可配置总结语言** - 通过 `.env` 文件选择中文（默认）或英文输出
- ✅ **智能语言转录** - Whisper 保留原始音频语言
- ✅ 节省存储空间（可选删除音频）
- ✅ 支持多种总结风格（简短/详细）
- ✅ 带时间戳的字幕文件（SRT 格式）
- ✅ YouTube 播放列表批量处理
- ✅ 本地 MP3 文件处理支持
- ✅ **Apple Podcasts 支持** - 下载并转录播客节目
- ✅ **批量处理** - 从文本文件处理多个输入
- ✅ **集中式日志系统** - 所有日志保存到 `logs/` 文件夹的时间戳文件
- ✅ **单独文件上传** - 每个处理的文件立即上传到 GitHub，防止批量失败

## 📊 数据工作流

```
输入源 → 处理流程 → 输出与存储
  ↓          ↓           ↓
YouTube   1. 下载      本地文件
播放列表    音频/字幕    (output/)
  或     2. 转录          ↓
Apple     3. AI 总结   GitHub 上传
Podcasts  4. 保存上传   （可选）
  或
本地 MP3
 文件夹
  或
批处理文件
（混合所有类型）
```

**处理流程：**
1. **输入**：YouTube URL、播放列表、Apple Podcast、本地 MP3 文件夹或批处理文件
2. **转录**：Whisper 将音频转换为文本（保留原始语言）
3. **总结**：OpenRouter/Perplexity AI 生成总结（可配置输出语言）
4. **输出**：SRT 转录 + Markdown 总结 + 增强报告
5. **上传**：每个文件在成功处理后立即上传到 GitHub

**主要优势：**
- 🔄 **单独文件处理**：每个文件独立上传
- 🛡️ **容错能力**：一个文件失败不会阻止其他文件
- 📝 **全面日志**：所有操作记录到时间戳文件
- 🌐 **语言灵活性**：转录保留原始语言；总结语言可配置

## 📋 系统要求

- Python 3.9+
- FFmpeg 4.0+
- 8GB+ RAM（推荐 16GB）
- 总结 API 密钥（二选一）：
  - OpenRouter API Key（有免费选项）
  - Perplexity API Key

## 🚀 快速开始

### 1. 安装依赖

**安装 FFmpeg**

```bash
# Mac
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# 从 https://ffmpeg.org 下载并添加到 PATH
```

**安装 Python 依赖**

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件并配置您的总结 API
# 选项 1：使用 OpenRouter（默认）
# SUMMARY_API=OPENROUTER
# OPENROUTER_API_KEY=your_api_key_here

# 选项 2：使用 Perplexity
# SUMMARY_API=PERPLEXITY
# PERPLEXITY_API_KEY=your_perplexity_api_key_here
```

**选择您的总结 API：**

您可以使用 OpenRouter 或 Perplexity AI 来生成总结。在 `.env` 文件中设置 `SUMMARY_API` 为您首选的服务。

**选项 1：获取 OpenRouter API Key（免费）：**
1. 访问 [OpenRouter.ai](https://openrouter.ai/)
2. 免费注册
3. 在设置页面获取 API Key
4. 在 .env 文件中设置 `SUMMARY_API=OPENROUTER`
5. 添加您的密钥：`OPENROUTER_API_KEY=your_api_key_here`

**选项 2：获取 Perplexity API Key：**
1. 访问 [Perplexity.ai](https://www.perplexity.ai/)
2. 注册并获取 API 访问权限
3. 从您的账户获取 API Key
4. 在 .env 文件中设置 `SUMMARY_API=PERPLEXITY`
5. 添加您的密钥：`PERPLEXITY_API_KEY=your_perplexity_api_key_here`

### 3. 运行程序

**方式一：使用快捷脚本（推荐）**

```bash
# 简单模式 - 只需输入 URL，使用默认设置
./quick-run.sh

# 完整模式 - 可选择总结风格、是否保留音频等选项
./run.sh

# 处理 YouTube 播放列表并上传到 GitHub
./playlist-to-github.sh

# 处理本地 MP3 文件夹并上传到 GitHub
./local-mp3-to-github.sh

# 批量处理输入文件（混合 URL 和路径）
./batch-run.sh
```

**GitHub 上传脚本特性：**
- 🎯 **自动化流程**：一条命令完成处理和上传
- 🎨 **交互式提示**：引导您完成所有选项
- 📊 **进度跟踪**：显示处理和上传状态
- ✅ **智能确认**：上传前询问确认
- 🛡️ **错误处理**：如果 GitHub 上传失败则保存到本地

**方式二：手动运行**

```bash
# 激活虚拟环境
source venv/bin/activate

# 基础使用 - 单个视频（默认模式）
python src/main.py "https://youtube.com/watch?v=xxxxx"
python src/main.py -video "https://youtube.com/watch?v=xxxxx"

# YouTube 播放列表
python src/main.py -list "https://youtube.com/playlist?list=xxxxx"

# 本地 MP3 文件夹
python src/main.py -local /path/to/mp3/folder

# 简短总结
python src/main.py -video "URL" --style brief

# 保留音频文件
python src/main.py -video "URL" --keep-audio

# 使用 cookies（会员视频）
python src/main.py -video "URL" --cookies cookies.txt

# 上传到 GitHub（处理过程中自动上传）
python src/main.py -video "URL" --upload
python src/main.py -list "URL" --upload
python src/main.py -local /path/to/mp3 --upload

# Apple Podcasts（单个节目 - 最新）
python src/main.py --apple-podcast-single "https://podcasts.apple.com/..."

# Apple Podcasts（节目的所有剧集）
python src/main.py --apple-podcast-list "https://podcasts.apple.com/..."

# 批量处理（混合 URL 和路径）
python src/main.py --batch input.txt
python src/main.py --batch input.txt --style brief --upload
```

## 📖 使用说明

### 命令行参数

```
python src/main.py [输入参数] [选项]

输入参数（互斥，选择其一）：
  -video URL                      YouTube 视频链接（未指定时为默认模式）
  -list URL                       YouTube 播放列表链接
  --apple-podcast-single URL      Apple Podcasts URL（仅最新节目）
  --apple-podcast-list URL        Apple Podcasts URL（节目的所有剧集）
  -local PATH                     本地 MP3 文件夹路径
  --batch FILE                    批处理输入文件（每行一个 URL 或路径）

可选参数：
  --cookies FILE                  cookies.txt 文件路径（用于会员视频）
  --keep-audio                   保留下载的音频文件（仅 YouTube）
  --style {brief|detailed}       总结风格（默认: detailed）
  --upload                       上传报告文件到 GitHub 仓库
```

### 处理会员视频

1. 安装浏览器扩展 [Get cookies.txt](https://chrome.google.com/webstore/detail/get-cookiestxt/bgaddhkoddajcdgocldbbfleckgcbcid)
2. 登录 YouTube
3. 导出 cookies 为 `cookies.txt`
4. 使用 `--cookies cookies.txt` 参数

### Python API 调用

```python
from src.main import process_video, process_playlist, process_local_folder
from pathlib import Path

# 处理单个视频
result = process_video(
    url="https://youtube.com/watch?v=xxxxx",
    keep_audio=False,
    summary_style="detailed"
)

# 处理播放列表
results = process_playlist(
    playlist_url="https://youtube.com/playlist?list=xxxxx",
    keep_audio=False,
    summary_style="detailed"
)

# 处理本地 MP3 文件夹
results = process_local_folder(
    folder_path=Path("/path/to/mp3/folder"),
    summary_style="detailed"
)

print(f"转录文件: {result['transcript_file']}")
print(f"总结文件: {result['summary_file']}")
print(f"报告文件: {result['report_file']}")
```

### 从文本文件批量处理

从单个文本文件处理多个输入（混合 YouTube 视频、播放列表、Apple Podcasts 和本地 MP3 文件夹）：

**1. 创建批处理输入文件**

创建一个文本文件（例如 `input.txt`），每行一个输入：

```text
# 这是注释 - 以 # 开头的行会被忽略
# 您可以在同一个文件中混合不同的输入类型

# YouTube 视频
https://www.youtube.com/watch?v=xxxxx

# YouTube 播放列表
https://www.youtube.com/playlist?list=xxxxx

# Apple Podcasts 节目
https://podcasts.apple.com/us/podcast/podcast-name/id123456789

# 本地 MP3 文件夹
/path/to/mp3/folder
./audio_files
```

**2. 运行批处理**

```bash
# 使用辅助脚本（推荐）
./batch-run.sh

# 或手动运行
python src/main.py --batch input.txt
python src/main.py --batch input.txt --style brief --upload
```

**功能特性：**
- ✅ **自动检测**：自动检测输入类型（YouTube、Apple Podcasts、本地路径）
- ✅ **混合输入**：在单个批次中处理不同类型
- ✅ **注释支持**：以 # 开头的行会被忽略
- ✅ **错误容忍**：失败的项目不会停止批处理
- ✅ **进度跟踪**：显示每个项目的详细进度
- ✅ **摘要报告**：最终摘要显示成功和失败的项目

**示例工作流程：**
```
1. 使用您的 URL 和路径创建 input.txt
2. 运行：./batch-run.sh
3. 选择总结风格（简短/详细）
4. 选择选项（cookies、keep-audio、upload）
5. 开始处理...（显示每个项目的进度）
6. 完成！摘要显示成功和失败的项目
```

### 自动化播放列表和 MP3 处理并上传到 GitHub

使用自动化脚本实现流程化工作流：

**1. YouTube 播放列表到 GitHub (`playlist-to-github.sh`)**

处理整个 YouTube 播放列表并自动上传报告到 GitHub：

```bash
# 交互模式（提示所有选项）
./playlist-to-github.sh

# 使用播放列表 URL 作为参数
./playlist-to-github.sh "https://youtube.com/playlist?list=xxxxx"
```

**功能特性：**
- ✅ 提示输入播放列表 URL
- ✅ 选择总结风格（简短/详细）
- ✅ 可选 cookies 支持（用于会员视频）
- ✅ 处理播放列表中的所有视频
- ✅ 上传前询问确认
- ✅ 显示详细的进度和结果

**示例工作流程：**
```
1. 输入播放列表 URL
2. 选择总结风格（简短/详细）
3. 使用 cookies？(y/N)
4. 处理播放列表中...（显示每个视频的进度）
5. 上传报告到 GitHub？(Y/n)
6. 完成！报告已上传到 GitHub
```

**2. 本地 MP3 到 GitHub (`local-mp3-to-github.sh`)**

处理本地 MP3 文件并自动上传报告到 GitHub：

```bash
# 交互模式（提示输入文件夹路径）
./local-mp3-to-github.sh

# 使用文件夹路径作为参数
./local-mp3-to-github.sh /path/to/mp3/folder
```

**功能特性：**
- ✅ 提示输入 MP3 文件夹路径
- ✅ 验证文件夹并统计 MP3 文件数量
- ✅ 选择总结风格（简短/详细）
- ✅ 处理所有 MP3 文件并转录
- ✅ 上传前询问确认
- ✅ 显示详细的进度和结果

**示例工作流程：**
```
1. 输入 MP3 文件夹路径
2. 找到 10 个 MP3 文件 ✓
3. 选择总结风格（简短/详细）
4. 处理 MP3 文件中...（显示进度）
5. 上传报告到 GitHub？(Y/n)
6. 完成！报告已上传到 GitHub
```

**GitHub 上传前置条件：**
- 必须在 `.env` 文件中配置 GitHub：
  ```bash
  GITHUB_TOKEN=你的个人访问令牌
  GITHUB_REPO=用户名/仓库名
  GITHUB_BRANCH=main
  ```
- 如未配置，报告将仅保存到本地

### GitHub 批量上传

使用专用上传脚本将文件夹中的所有 Markdown 文件上传到 GitHub 仓库：

**配置：**
```bash
# 在 .env 文件中配置 GitHub
GITHUB_TOKEN=你的个人访问令牌
GITHUB_REPO=用户名/仓库名
GITHUB_BRANCH=main
```

**使用方法：**
```bash
# 上传 output/reports 中的所有 .md 文件到 GitHub
python src/upload_to_github.py output/reports

# 上传到不同的远程文件夹
python src/upload_to_github.py output/summaries --remote-folder summaries

# 预览将要上传的文件（试运行模式）
python src/upload_to_github.py output/reports --dry-run
```

**功能特性：**
- 📤 上传指定文件夹中的所有 .md 文件
- 🔄 自动创建或更新 GitHub 中的文件
- 📊 显示上传进度和摘要
- ✅ 上传前交互式确认
- 🛡️ 试运行模式预览更改

**示例输出：**
```
找到 15 个 markdown 文件：
  - 20251101_1430_TechChannel_intro-to-ai.md
  - 20251101_1445_DevTips_python-best-practices.md
  ...

准备上传 15 个文件到 GitHub
仓库: username/video-summaries
分支: main
远程文件夹: reports

继续? [y/N]: y

[1/15] 上传中: 20251101_1430_TechChannel_intro-to-ai.md
✓ 上传成功
  URL: https://github.com/username/video-summaries/blob/main/reports/...

上传摘要：
总文件数: 15
成功: 15
✓ 所有文件上传成功！
```

## 📁 输出文件

```
output/
├── transcripts/
│   └── [video_id]_transcript.srt      # 字幕文件
├── summaries/
│   └── [video_id]_summary.md          # 总结文件（按视频ID命名）
└── reports/
    └── [timestamp]_[视频标题].md       # 报告文件（按时间和标题命名）
```

### 报告文件格式

报告文件命名格式：`YYYYMMDD_HHMM_[上传者]_[内容标题].md`

例如：`20251029_1535_TechChannel_introduction-to-python-programming.md`

文件内容包含：
- 视频标题和时长
- AI 生成的总结
- 参考信息（视频 ID 和 URL）

### 总结文件格式示例

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

## 💡 核心见解
[深度分析和启发]

---

## 📎 参考信息

**视频 ID**: 

**视频链接**: 
```

## ⚙️ 配置说明

编辑 `.env` 文件自定义配置：

```bash
# === AI 模型配置 ===
# 总结 API 提供商（'OPENROUTER' 或 'PERPLEXITY'）
SUMMARY_API=OPENROUTER

# OpenRouter API 密钥（如果 SUMMARY_API=OPENROUTER 则必需）
OPENROUTER_API_KEY=your_api_key_here
# OpenRouter 模型名称
OPENROUTER_MODEL=deepseek/deepseek-r1

# Perplexity API 密钥（如果 SUMMARY_API=PERPLEXITY 则必需）
PERPLEXITY_API_KEY=your_perplexity_api_key_here
# Perplexity 模型名称
PERPLEXITY_MODEL=sonar-pro

# === Whisper 配置 ===
# Whisper 模型大小（tiny/base/small/medium/large）
WHISPER_MODEL=base

# 转录语言设置（zh/en/auto）
# 注意：Whisper 保留原始音频语言
WHISPER_LANGUAGE=zh

# === 总结语言配置 ===
# AI 生成总结的输出语言（zh/en）
# 默认：zh（中文）
# - zh：生成中文总结
# - en：生成英文总结
# 注意：这仅控制总结输出语言。
#       转录语言由音频内容决定。
SUMMARY_LANGUAGE=zh

# === 音频配置 ===
# 音频质量（kbps）
AUDIO_QUALITY=64

# 处理后保留音频文件
KEEP_AUDIO=false

# === GitHub 上传配置（可选）===
# GitHub 个人访问令牌（需要 'repo' 权限）
GITHUB_TOKEN=your_github_token_here

# 目标仓库（格式：username/repo）
GITHUB_REPO=username/repository_name

# 目标分支（默认：main）
GITHUB_BRANCH=main

# === 日志配置 ===
# 所有日志都保存到 logs/ 文件夹中的时间戳文件
# 控制台输出显示 INFO 级别及以上
# 日志文件包含 DEBUG 级别及以上
```

**模型选择建议：**
- `tiny`: 最快，准确度较低（适合快速测试）
- `base`: 平衡速度和准确度（推荐）
- `small`: 更准确，速度较慢
- `medium/large`: 最准确，需要更多资源

**语言配置：**
- **WHISPER_LANGUAGE**：控制音频转录语言检测（保留原始音频语言）
- **SUMMARY_LANGUAGE**：控制 AI 总结输出语言（zh=中文，en=英文）
  - 设置为 `zh` 生成中文总结（默认）
  - 设置为 `en` 生成英文总结
  - 转录始终保持原始音频语言

**GitHub 上传配置：**
要在处理后启用自动 GitHub 上传：
1. 创建具有 `repo` 权限的 GitHub 个人访问令牌
2. 在 `.env` 文件中添加以下内容：
   ```bash
   GITHUB_TOKEN=your_token_here
   GITHUB_REPO=username/repo_name
   GITHUB_BRANCH=main
   ```
3. 使用 `--upload` 标志或自动化脚本（`playlist-to-github.sh`、`local-mp3-to-github.sh`）

**重要上传行为：**
- 每个文件在**成功处理后立即**上传到 GitHub
- 这可防止一个文件失败阻止其他上传
- 如果文件处理失败，它会被跳过，并继续处理下一个文件
- 失败的上传会被记录但不会停止工作流

## 🧪 运行测试

```bash
# 运行所有测试
python -m unittest discover tests

# 运行特定测试
python -m unittest tests.test_youtube
python -m unittest tests.test_transcriber
python -m unittest tests.test_summarizer
```

## 📋 日志系统

应用程序具有全面的日志系统：

**日志位置：**
- **控制台**：INFO 级别及以上（用户友好的进度消息）
- **日志文件**：DEBUG 级别及以上（详细的技术信息）
  - 位置：`logs/youtube_summarizer_[YYYYMMDD_HHMMSS].log`
  - 格式：`2025-11-02 15:30:45 - INFO - [模块] 消息`

**日志内容：**
- 处理步骤和进度
- API 请求和响应
- 文件操作（读/写/上传）
- 带堆栈跟踪的错误详情
- GitHub 上传状态
- 性能指标

**优势：**
- 🔍 **调试**：详细的日志帮助排查问题
- 📊 **审计跟踪**：所有操作的完整记录
- 🕐 **时间戳**：每个会话都有唯一的日志文件
- 🎯 **双重输出**：控制台显示关键信息，文件显示所有内容

## ⚠️ 注意事项

### 安全与合规
- ⚠️ **切勿**将 `cookies.txt` 提交到 Git
- ⚠️ **切勿**分享或二次分发会员内容
- ⚠️ **仅用于**个人学习使用
- ⚠️ 遵守 YouTube 服务条款

### 性能建议
- 长视频（>1小时）建议使用 `tiny` 或 `base` 模型
- 批量处理时注意 API 速率限制
- 首次运行会下载 Whisper 模型（~150MB for base）

## 🐛 故障排除

### HTTP 403 错误
```bash
# 更新 yt-dlp
pip install -U yt-dlp
```

### Cookies 过期
重新导出浏览器 cookies

### Whisper 转录太慢
- 降低模型大小（使用 `tiny` 或 `base`）
- 或安装 `faster-whisper`（可选）

### API 限流
程序会自动重试，如果频繁失败，稍后再试

### FFmpeg 未找到
确保 FFmpeg 已安装并添加到系统 PATH

## 📚 技术栈

- **yt-dlp**: YouTube 视频下载
- **OpenAI Whisper**: 语音转文字
- **OpenRouter**: AI 文本总结
- **FFmpeg**: 音频处理

## 🔮 未来计划

- [x] 支持批量处理多个视频（YouTube 播放列表）
- [x] 本地音频文件处理支持
- [x] 可配置总结语言（中文/英文）
- [x] 集中式日志系统（带时间戳的日志文件）
- [x] GitHub 仓库集成实现自动备份
- [x] 单独文件上传防止批量失败
- [x] Apple Podcasts 支持
- [x] 批量处理（混合输入类型）
- [ ] 添加 Web UI 界面
- [ ] 支持更多视频平台（Bilibili、Vimeo）
- [ ] 多语言翻译功能
- [ ] 导出 PDF/Word 格式
- [ ] 视频关键帧截图

## 📄 License

MIT License

---

**最后更新**: 2025-11-05

## 📝 最新更改 (2025-11-05)

### Apple Podcasts 支持
- ✅ 支持从 Apple Podcasts 下载和转录节目
- ✅ 单个节目处理（最新剧集）
- ✅ 节目批量处理（所有剧集）
- ✅ 自动音频下载和格式检测

### 批量处理功能
- ✅ 从文本文件处理多个输入
- ✅ 支持混合输入类型（YouTube、Apple Podcasts、本地 MP3）
- ✅ 自动输入类型检测
- ✅ 注释和空行支持
- ✅ 错误容忍和详细进度跟踪
- ✅ 批处理辅助脚本 (`batch-run.sh`)

### 集中式日志系统
- ✅ 将所有 `print()` 语句替换为结构化日志
- ✅ 双重输出：控制台（INFO+）和日志文件（DEBUG+）
- ✅ `logs/` 文件夹中的时间戳日志文件
- ✅ 全面的错误跟踪和调试信息

### 单独文件上传
- ✅ 每个文件在处理后立即上传到 GitHub
- ✅ 防止一个失败阻止其他上传
- ✅ 改进批量操作的容错能力
- ✅ 适用于播放列表和本地 MP3 文件夹

### 可配置总结语言
- ✅ `.env` 文件中的新 `SUMMARY_LANGUAGE` 选项
- ✅ 在中文（zh）或英文（en）总结之间选择
- ✅ 默认：中文（zh）
- ✅ 转录始终保留原始音频语言

### 环境配置更新
- ✅ 添加 `SUMMARY_API` 设置（OPENROUTER/PERPLEXITY）
- ✅ 添加 `SUMMARY_LANGUAGE` 设置（zh/en）
- ✅ 增强 GitHub 配置文档
- ✅ 改进 `.env.example` 中的注释和组织