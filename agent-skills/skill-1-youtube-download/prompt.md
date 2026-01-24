# Skill 1: 下载 YouTube 音频或字幕

## 适用场景
当需要获取 YouTube 视频的原始音频（MP3）或字幕（SRT）时使用。

## 环境设立（必需）
1. 安装 FFmpeg（系统依赖）
2. 安装 Python 依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 如需会员视频，准备 `cookies.txt`

## 输入
- `url`：YouTube 视频 URL
- `cookies`（可选）：cookies 文件路径
- `lang`（可选）：字幕语言，默认 `zh`
- `output_dir`（可选）：输出目录，默认 `output/downloads`

## 输出
- `subtitle_path`：若下载到字幕，将返回 SRT 路径
- `audio_path`：若无字幕，将返回 MP3 路径
- `video_info`：视频元信息（标题、作者、上传时间、播放数等）

## 执行命令
```bash
python agent-skills/skill-1-youtube-download/scripts/download_youtube.py \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --lang zh \
  --output-dir output/downloads
```

## 说明
- 脚本优先尝试下载字幕；若失败则下载 MP3。
- 输出目录会自动创建。
