# Skill 3: SRT -> OpenRouter 总结

## 适用场景
需要基于 SRT 字幕生成结构化 Markdown 总结，并在 Reference 部分附带视频元信息。

## 环境设立（必需）
1. 配置 OpenRouter API Key：
   ```bash
   export OPENROUTER_API_KEY=your_key
   ```
2. 可选：指定免费模型
   ```bash
   export OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free
   ```
3. 安装 Python 依赖：
   ```bash
   pip install -r requirements.txt
   ```

## 输入
- `srt_path`：字幕文件路径
- `youtube_url`（可选）：用于抓取作者、标题、上传时间、点赞数、播放数等
- `language`（可选）：输出语言，默认 `zh`
- `model`（可选）：OpenRouter 免费模型名
- `output_dir`（可选）：输出目录，默认 `output/summaries`

## 输出
- `summary_path`：Markdown 总结文件路径
- `reference`：在文件末尾的 Reference 信息

## 执行命令
```bash
python agent-skills/skill-3-srt-to-summary/scripts/summarize_srt.py \
  --srt-path output/transcripts/VIDEO_ID.srt \
  --youtube-url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --language zh \
  --output-dir output/summaries
```

## 总结模板（示意）
```
# 标题

## 📝 内容概要
...

## 🎯 关键要点
- ...

## ⏱ 时间线
- ...

## 💡 核心见解
...

---

## 📎 Reference
- Author: ...
- Title: ...
- Upload Date: ...
- Views: ...
- Likes: ...
- Video URL: ...
- Video ID: ...
```
