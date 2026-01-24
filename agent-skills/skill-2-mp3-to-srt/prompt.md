# Skill 2: MP3 转 SRT

## 适用场景
当已有 MP3 音频文件，需要生成时间轴字幕（SRT）时使用。

## 环境设立（必需）
1. 安装 FFmpeg（系统依赖）
2. 安装 Python 依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 可选：设置 `.env` 中的 `WHISPER_MODEL`、`WHISPER_LANGUAGE`

## 输入
- `mp3_path`：MP3 文件路径
- `language`（可选）：`zh/en/auto`，默认 `auto`
- `output_dir`（可选）：输出目录，默认 `output/transcripts`

## 输出
- `srt_path`：生成的字幕路径
- `detected_language`：Whisper 识别语言

## 执行命令
```bash
python agent-skills/skill-2-mp3-to-srt/scripts/mp3_to_srt.py \
  --mp3-path output/downloads/VIDEO_ID.mp3 \
  --language auto \
  --output-dir output/transcripts
```
