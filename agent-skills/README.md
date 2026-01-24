# Agent Skills（基于 ytb_video_summary）

本目录将仓库内的处理流程拆分为 4 个可复用的 agent skills，方便在 Claude Code / Open Code 等环境中按步骤执行。

## ✅ 总体流程概览

1. **下载 YouTube 音频或字幕**：获取视频元信息，优先下载字幕，若无字幕则下载音频（MP3）。
2. **MP3 转 SRT**：使用 Whisper 对音频进行转写，输出时间轴字幕（SRT）。
3. **SRT 总结**：读取字幕内容并调用 OpenRouter 免费模型生成 Markdown 总结，同时写入视频元信息（作者、标题、上传时间、点赞数、播放数等）作为 Reference。
4. **上传到 GitHub**：将本地 Markdown 文件批量上传到指定 GitHub repo/folder。

## 📁 目录结构

```
agent-skills/
  README.md
  youtube-download/
  mp3-to-srt/
  srt-to-summary/
  upload-to-github/
```

每个 skill 目录均包含：

- `SKILL.md`：技能说明（含 metadata 与执行指引）
- `scripts/`：可执行脚本（尽量使用 Python）

## 🧩 建议执行顺序

1. `youtube-download`
2. `mp3-to-srt`
3. `srt-to-summary`
4. `upload-to-github`
