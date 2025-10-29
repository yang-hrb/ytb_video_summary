# 快速开始指南

## 🎯 项目已创建完成！

所有必要的文件和目录结构已经生成。以下是开始使用的步骤：

## 📋 下一步操作

### 1. 安装 FFmpeg（必需）

**Windows:**
```cmd
# 从 https://ffmpeg.org/download.html 下载
# 解压并添加到系统 PATH
```

**Mac:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg
```

### 2. 设置 Python 环境

```cmd
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境（Windows）
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置 API Key

```cmd
# 复制环境变量模板
copy .env.example .env

# 编辑 .env 文件，添加你的 OpenRouter API Key
notepad .env
```

**获取 OpenRouter API Key:**
1. 访问 https://openrouter.ai/
2. 注册账号（免费）
3. 在设置页面获取 API Key
4. 将 API Key 填入 `.env` 文件

### 4. 测试运行

```cmd
# 测试一个短视频
python src\main.py "https://youtube.com/watch?v=xxxxx"

# 或使用简短总结模式
python src\main.py "URL" --style brief
```

## 📁 项目结构说明

```
ytb_video_summary/
├── config/                 # 配置模块
│   ├── __init__.py
│   └── settings.py        # 环境变量和路径配置
│
├── src/                   # 源代码
│   ├── __init__.py
│   ├── main.py           # 主程序入口
│   ├── youtube_handler.py # YouTube 下载
│   ├── transcriber.py    # Whisper 转录
│   ├── summarizer.py     # AI 总结
│   └── utils.py          # 工具函数
│
├── tests/                # 单元测试
│   ├── test_youtube.py
│   ├── test_transcriber.py
│   └── test_summarizer.py
│
├── output/               # 输出目录
│   ├── transcripts/      # 字幕文件
│   ├── summaries/        # 总结文件（按视频ID）
│   └── reports/          # 报告文件（按时间和标题）
│
├── temp/                 # 临时音频文件
├── .env.example         # 环境变量模板
├── .gitignore           # Git 忽略配置
├── requirements.txt     # Python 依赖
├── README.md           # 项目说明
└── prd.md              # 产品需求文档
```

## 🔧 配置选项

在 `.env` 文件中可以自定义以下选项：

```bash
# Whisper 模型（tiny/base/small/medium/large）
WHISPER_MODEL=base

# 语言（zh/en/auto）
WHISPER_LANGUAGE=zh

# 音频质量（kbps）
AUDIO_QUALITY=64

# 是否保留音频文件
KEEP_AUDIO=false
```

## 🎬 使用示例

### 基础使用
```cmd
python src\main.py "https://youtube.com/watch?v=dQw4w9WgXcQ"
```

### 会员视频（需要 cookies）
```cmd
# 1. 使用浏览器扩展导出 cookies.txt
# 2. 将 cookies.txt 放在项目根目录
# 3. 运行命令
python src\main.py "URL" --cookies cookies.txt
```

### 保留音频文件
```cmd
python src\main.py "URL" --keep-audio
```

### 简短总结
```cmd
python src\main.py "URL" --style brief
```

## 🧪 运行测试

```cmd
# 运行所有测试
python -m unittest discover tests

# 运行特定测试
python -m unittest tests.test_youtube
```

## 📊 输出说明

处理完成后，会生成以下文件：

1. **字幕文件**: `output/transcripts/[video_id]_transcript.srt`
   - 包含时间戳的字幕
   - SRT 格式

2. **总结文件**: `output/summaries/[video_id]_summary.md`
   - Markdown 格式
   - 按视频 ID 命名

3. **报告文件**: `output/reports/[timestamp]_[视频标题].md`
   - Markdown 格式
   - 按时间戳和视频标题命名
   - 包含视频 ID 和 URL 作为参考信息
   - 例如：`20251029_1535_如何学习Python编程.md`

## ⚠️ 常见问题

### 1. 缺少 FFmpeg
**错误**: `ffmpeg not found`
**解决**: 安装 FFmpeg 并添加到系统 PATH

### 2. API Key 未设置
**错误**: `OpenRouter API key is required`
**解决**: 在 `.env` 文件中设置 `OPENROUTER_API_KEY`

### 3. 首次运行较慢
**原因**: Whisper 需要下载模型文件（~150MB for base）
**说明**: 这是正常现象，只在首次运行时发生

### 4. HTTP 403 错误
**解决**: 更新 yt-dlp
```cmd
pip install -U yt-dlp
```

## 📚 更多资源

- **完整文档**: 查看 `README.md`
- **产品需求**: 查看 `prd.md`
- **GitHub Issues**: 报告问题或提建议

## 🎉 开始使用吧！

现在你已经准备好开始使用这个工具了。祝你使用愉快！

---

如有问题，请查看 README.md 或提交 GitHub Issue。
