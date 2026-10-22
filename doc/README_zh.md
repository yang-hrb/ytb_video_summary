# YouTube 转写与摘要工具

[English README](../README.md)

处理 YouTube 视频、播放列表、频道近期更新，或本地文件夹中的 MP3。视频已有字幕时优先读取字幕；需要转写时使用 Whisper。工具生成 Markdown 报告，可选择上传到 GitHub。

## 环境要求

- Python 3.9 或更新版本
- FFmpeg
- OpenRouter API Key，或已安装并完成认证的 `agy` CLI

Apple Silicon 上默认使用 `mlx-whisper`，其他平台默认使用 `openai-whisper`。Whisper 模型可能需要较多内存和磁盘空间。

## 安装

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

在 `.env` 中设置摘要服务：

- `SUMMARY_PROVIDER=openrouter_free`（默认）：填写 `OPENROUTER_API_KEY`。
- `SUMMARY_PROVIDER=agy_cli`：安装并认证 `agy`，无需 OpenRouter Key。

若要上传 GitHub，还需设置 `GITHUB_TOKEN` 和 `GITHUB_REPO`（格式为 `owner/repository`）。`GITHUB_BRANCH` 默认为 `main`。不传 `--upload` 时，报告只保存在本地。

## 使用方法

在仓库根目录、激活虚拟环境后运行。摘要风格默认为 `detailed`；可用 `--style brief` 选择简要风格。

```bash
# 处理单个 YouTube 视频
python src/main.py -video "https://youtube.com/watch?v=VIDEO_ID"

# 处理播放列表
python src/main.py -list "https://youtube.com/playlist?list=PLAYLIST_ID"

# 处理文件夹内的 MP3（不是单个文件）
python src/main.py -local ./audio_files

# 扫描频道：channellist.txt 中每行一个频道 URL
python src/main.py --scan channellist.txt --max-hours 4

# 处理后上传报告
python src/main.py -video "https://youtube.com/watch?v=VIDEO_ID" --upload

# 已有完成记录时仍重新处理
python src/main.py -video "https://youtube.com/watch?v=VIDEO_ID" --force
```

会员或其他需要登录的视频可通过 `--cookies cookies.txt` 使用 Netscape 格式的 Cookie 文件。浏览器 Cookie 默认关闭，可显式传入 `--cookies-from-browser`，并通过 `--browser chrome|edge|firefox` 指定浏览器。

其他选项包括：`--batch FILE`（每行一个 URL 或本地路径）、`--status`、`--list-failed`、`--list-resumable`、`--resume-only` 和 `--daily-summary [YYYYMMDD]`。完整列表请运行 `python src/main.py --help`。

## 频道扫描

`--scan FILE` 按行读取频道 URL，空行和以 `#` 开头的注释会被忽略。程序检查最近两天发布的视频，按从旧到新的顺序处理选中的视频，并生成每日摘要。如果频道列表文件不存在，程序会创建示例文件；请先加入频道 URL 再扫描。

扫描通过 `logs/scan.lock` 防止重复并发运行。`--max-hours` 设置进程内时间上限；截止时尚未启动的视频会标记为 `PENDING_KILLED`，之后的扫描会再次处理，且当前扫描仍会生成部分结果摘要。`scripts/daily_scan.sh` 可用于定时执行；需自行配置 cron 或系统任务计划。

## 输出与去重

```text
output/
├── transcripts/       # SRT 字幕/转写文本
├── summaries/         # 中间摘要
└── summary/           # 最终 Markdown 报告和 daily_digest/

logs/
├── ytb_summary_track.db
├── two_time_fail.txt
└── *.log
```

`logs/ytb_summary_track.db` 是完成记录复用的唯一依据。只有数据库中的报告路径仍存在时，`COMPLETED` 记录才会被复用；复用后不会重新下载、转写、总结或上传。YouTube 视频使用视频 ID 去重；本地 MP3 使用前 8 MB 内容和文件大小生成 ID，因此重命名不会触发重复处理。使用 `--force` 或别名 `--no-reuse` 可跳过去重。

首次初始化时，程序可能将旧的 `logs/run_track.db` 迁移并改名为 `logs/run_track_backup.db`；新状态写入 `ytb_summary_track.db`。

## 配置

常用 `.env` 设置：

- `SUMMARY_PROVIDER`、`OPENROUTER_API_KEY`、`MODEL_PRIORITY_1` 至 `MODEL_PRIORITY_3` 和 `MODEL_FALLBACK`：控制摘要服务。OpenRouter 会按模型优先级尝试，并对临时错误重试；`agy_cli` 使用完整 SRT。
- `SUMMARY_LANGUAGE`：摘要语言，支持 `zh` 和 `en`，默认为 `zh`。`--style` 控制 `brief` 或 `detailed` 风格。
- `WHISPER_MODEL`、`WHISPER_LANGUAGE` 和 `WHISPER_BACKEND`：控制转写。`WHISPER_BACKEND=auto` 会在 Apple Silicon 上选择 MLX，其他平台选择 OpenAI Whisper。
- `GITHUB_TOKEN`、`GITHUB_REPO` 和 `GITHUB_BRANCH`：配置可选的 GitHub 上传。

更多选项和默认值见 `.env.example`。OpenRouter 摘要最多使用 60,000 个转写字符，超出的尾部会被截掉并记录警告；`agy_cli` 使用完整 SRT。

## 开发

运行单元测试：

```bash
python -m unittest discover tests
```

测试使用 `unittest`；网络和外部服务调用应使用 mock。辅助诊断脚本见 [scripts/README.md](../scripts/README.md)。
