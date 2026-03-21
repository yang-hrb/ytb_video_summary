# YouTube 视频字幕提取与AI总结工具

[English Documentation (英文 README)](../README.md)

🎥 自动提取 YouTube 视频（包括会员专属内容）的字幕，并使用 AI 生成内容的深度结构化摘要。

## ✨ 核心特性

- ✅ 支持 YouTube 公开视频及会员频道专属内容
- ✅ 自动提取原生字幕，或使用本地 AI Whisper 进行音频转写识别
- ✅ **Apple Silicon (M系列芯片) 专项优化** - 原生内置 `mlx-whisper`，使得在 Mac M1/M2/M3 等设备的转写速度极速提升。
- ✅ 高质量 AI 内容总结 (基于 OpenRouter 接口，支持多大模型故障无缝切换，实现高可用 Waterfall)
- ✅ **动态指令 Prompting** - 基于频道/Up主的类型，动态为其分配最合适的 AI 总结指引指令（比如 Talk show, 教程, 新闻）。
- ✅ **Web 面板 (FastAPI 驱动)** - 附带一个内置可视化的看板 UI，提交处理列队、查看执行数据、和实现结果的一键 ZIP 批量下载功能。
- ✅ **智能防断点与 SQLite 状态追踪** - 具有超强容错率！底层的管线状态机允许程序在任何中断（如`TRANSCRIBE_FAILED` 或 `SUMMARIZE_FAILED`）后无损自动恢复，无需重复耗时下载。
- ✅ **关注列表 Watchlist 与每日摘要 (Daily Digest)** - 可挂载后台守护进程持续监控喜爱的频道，生成汇总报告并自动整理成可读性极强的每日汇总。
- ✅ 支持 **Apple Podcasts 苹果播客** 及 **本地 MP3 文件夹** 批量处理
- ✅ 全面支持配置总结内容的输出语言（如：中/英），于 `.env` 配置
- ✅ 支持文本文档导入混排批处理 (Batch processing)
- ✅ 支持自动向 GitHub Repo 上传 Markdown 生成文件用于备份与发布

## 📊 数据处理流

```text
输入源 → 处理管线 (由 SQLite 全程追踪) → 输出与存储
      ↓                       ↓                                 ↓
   YouTube               1. 下载                         本地存盘
    播放列表               音频或字幕                    (报告, 字幕流)
      或者                 2. Whisper 转写                       ↓
Apple Podcasts           3. AI 总结                     Zip 归档批量导出
      或者                 4. 保存并上传                   (通过 Dashboard) 
  本地 MP3                       ↑                              ↓
      或者                 5. 数据库状态跃迁                 GitHub 远端同步
 Web 列队前端                                                (可选项)
```

## 📋 系统要求

- Python 3.9+
- FFmpeg 4.0+
- 8GB+ 内存 (推荐 16GB)
- OpenRouter API Key（有大量免费模型可用）

## 🚀 快速上手 (Quick Start)

### 1. 安装系统依赖

**安装 FFmpeg**
```bash
# Mac (Homebrew)
brew install ffmpeg
```

**安装 Python 依赖配置库**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量
```bash
cp .env.example .env
# 打开并编辑 .env 文件，把你的 OPENROUTER_API_KEY 填在里面
```

### 3. 使用 Web 面板操控 (推荐方法)

启动基于 FastAPI 的应用监控与交互仪表盘，轻松管理作业：

```bash
./start_dashboard.sh
```
随后利用浏览器访问 **[http://127.0.0.1:8999/dashboard](http://127.0.0.1:8999/dashboard)** ！
- 可提交单个视频或是完整的 Playlist 链接。
- 跟踪错误、成功、耗时的大盘数据。
- 可以一键下载所打包产生的摘要 Markdown 及对应的 Transcript 字幕文件所构成的 Zip 压缩包。

### 4. 通过终端命令行 (CLI) 操作

```bash
# 基本使用 - 提取并总结单视频
python src/main.py "https://youtube.com/watch?v=xxxxx"

# 批量处理某个 YouTube 播放列表
python src/main.py -list "https://youtube.com/playlist?list=xxxxx"

# Watchlist 守护进程 - 在后台周期性监控指定频道
python src/main.py --watch-daemon --watch-time 3600

# 生成每日看板报告 (Daily Summary)
python src/main.py --daily-summary

# 中断恢复 - 只重试那些曾失败或中断的任务
python src/main.py --resume-only

# 诊断与查看系统状态
python src/main.py --status
python src/main.py --list-failed
```

## 📖 详细使用指南

### 命令行参数一览

```
输入源参数 (彼此互斥):
  -video URL                      YouTube 单视频 URL
  -list URL                       YouTube 播放列表 URL
  --apple-podcast-single URL      Apple Podcast 播客 URL (提取最新一集)
  --apple-podcast-list URL        Apple Podcast 播客 URL (提取整个节目集合)
  -local PATH                     处理本地给定的某个 MP3 文件夹路径
  --batch FILE                    按照文本批量处理 (文件内可混排上述规则)

诊断与数据库状态操作:
  --status                        展示大盘的执行追踪数据与统计
  --list-failed                   列举哪些任务失败，以及报错的具体阶段/原因
  --list-resumable                列举哪些任务可被恢复再次尝试
  --resume-only                   重跑所有断点 / 故障流

守护与总结操作:
  --watch-daemon                  将检查程序变为长运行常挂的守护进程
  --watch-run-once                触发执行一次完整的列表检查
  --import-watchlist FILE         导入文本文档中的 UP 主进入系统监管
  --daily-summary                 生成系统截止目前生成的每日播报 Digest

可选辅助参数:
  --cookies-from-browser          启用本机浏览器内的 Cookies (免受限制) (强烈推荐)
  --browser {chrome,edge,firefox} 指定要借用 Cookie 的浏览器
  --style {brief|detailed}        摘要体裁与篇幅 (默认: detailed)
  --upload                        执行后将结果自动同步推送给绑定的 GitHub 仓库
```

### 自动化监控及 GitHub 关联
如果你在 `.env` 中填写了解锁的 `GITHUB_TOKEN`，`GITHUB_REPO` 及 `GITHUB_BRANCH`，一旦指定了 `--upload` 命令，该项目所产生的 `.md` 摘要报表就会以无感知的形式实时同步并提交推送至你的 GitHub 远端页面上（可用作构建公开资源库或者 Notion 备份）。同时所有的运行动作受 `run_track.db` 追溯保护去重，绝对不会被冗余地重复调用 API 消费额度。

## 📁 输出文件结构与预览

```text
output/
├── transcripts/
│   └── [video_id]_transcript.srt      # 处理出来的源语字幕文档
├── summaries/
│   └── [video_id]_summary.md          # 内部处理摘要
├── reports/
│   └── [时间戳]_[频道主]_[视频名].md  # 最终定版带有版式的排版报文
└── zips/
    └── summary_bundle_job_*.zip       # 面板(Dashboard)提供给前端下发的打包集

logs/
└── ytb_summarizer_[时间戳].log     # 流水日志文件
run_track.db                           # SQLite 状态追迹核心文件
```

## ⚙️ 个性化配置 (.env)

常用的个性化定制可调节参数：
- `WHISPER_BACKEND`: 设为 `auto` 则能在 M系列设备上点燃极速的 `mlx-whisper`，未满足时启用标准的 `openai` whisper 模式。
- `SUMMARY_LANGUAGE`: 控制 AI 产生的对应语言，`zh` 为中文，`en` 为英语。
- `OPENROUTER_MODEL` & `MODEL_PRIORITY_{1..3}`: 创建健壮的模型熔断机制（瀑布接力），当主模型在遇到 429 或 500 断网限流时，程序能秒接预案模型平滑续写不中断。

## 🔮 研发路线 (Future Plans)

- [x] 批量支持与 YouTube 列表流支持
- [x] 本地媒体，及聚合播客的支持 
- [x] 时间戳集中的日志系统 
- [x] 远端 GitHub Repo 的对接集成
- [x] 高级的 SQLite 追迹状态机引擎与智能断点恢复 `Smart Resume`
- [x] 可视化前端 Web 交互 Web UI 
- [x] 智能频道特征预判，提供定制 Prompt 及 Daily Digest 分发
- [ ] 更丰富的全媒体矩阵引入（如 Bilibili 或 Vimeo 等平台）
- [ ] 更多的自然语言翻译特色映射支持
- [ ] 转写为 PDF 或 Word 规格下发
- [ ] 提供基于 FFmpeg 的高阶视频智能打点截图插帧支持

---

**最终更新时间**: 2026-03-20

## 📝 近期重要升级概要 (v2.1 / 2026-03)

针对了系统的健壮性，使用便利度，和可视化反馈进行了从 第1相至第4相 (Phase 1-4) 量级脱胎换骨的调整：
- ✅ **可视化 Dashboard 交互板**: 基于 FastAPI 承接引擎的前端，可轻易掌控批处理，查阅图表并将战利品打包为 ZIP 供本地检阅。
- ✅ **SQLite 管线状态机**: 取代松散逻辑。目前严格追踪每一次的流转 (`DOWNLOAD`, `TRANSCRIBE`, `SUMMARIZE`)。即使由于断点、网络或 API 崩坏导致被掐断，现在均能利用 `--resume-only` 基于残破的数据接力完工。
- ✅ **通道关注及日报体系**: 构建了针对创作者流更新的精准捕获体系。使用独立数据库防重排。同时结合强大的日志清洗每日凌晨吐出一份精致悦目的 `daily_digest` 纯文本快报。
- ✅ **定制分析逻辑 (Dynamic Prompts)**: 抛弃通用话术，采用字典注入机制针对不同类型的播放者（科普向，游戏向，实时直播向）给出最契合灵魂的引导指令总结模版以确保萃取的信息极具含金量。
- ✅ **释放 Apple 芯片天性**: 底层完成封装改写，现在原生地注入启动 `mlx-whisper`。在 Apple 硬件下性能飙升，完全规避因为缺乏加速引发的龟速卡顿。 