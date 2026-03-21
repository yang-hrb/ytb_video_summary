# Phase 4 实施与测试日志

## 1. 实施细节

根据 `doc/antigravity_action_plan_20250319.md` 中 Phase 4: Dashboard + Web UI + ZIP 导出的规划，完成了以下开发任务：

### 1.1 数据库结构升级 (`src/run_tracker.py`)
在 SQLite 数据库初始化的现有流程中，新增了 Phase 4 的两个核心表：
- `web_jobs`: 用于追踪通过 Dashboard 提交的批量摘要生成任务状态及其配置（包含队列管理和导出记录）。
- `web_job_runs`: 映射单个批量任务 (job) 与其底层每个视频的具体处理结果 (run)。

### 1.2 Web 后端与任务调度实现
创建了所需的 Python 服务模块：
- **`src/dashboard_app.py`**: 基于 FastAPI 的 Web 应用程序。实现了前端请求路由，包括 `/dashboard`（静态 UI 投递）、`/api/runs` 和 `/api/stats`（看板指标与列表接口），以及 `/api/jobs/*` (异步队列启动与 ZIP 下载)。
- **`src/dashboard_service.py`**: 数据读取层。查询 `runs` 表和 `file_storage` 表聚合生成 Dashboard 统计数据，并实现搜索与分页查询接口。
- **`src/job_manager.py`**: 任务管理中心。当新请求提交时，初始化任务至数据库。借用 FastAPI 的 `BackgroundTasks` 或子进程发起 `src/main.py -list` 后台调度任务，并回调更新运行状况及生成 Zip 打包。
- **`src/zip_exporter.py`**: 结果文件归档器。在批处理完成后查询数据库抓取所有的 Transcript `.srt`、Summary `.md` 以及生成附带元信息的清单文件 (Metadata metadata/runs.csv & manifest)，封包输出至 `output/zips/` 目录下备下载查阅。

### 1.3 前端 UI 和文档
- **`web/dashboard.html`**: 使用原生 HTML/CSS/JS (Vanilla JS) 实现了轻量级的前端交互框架。实现了任务快速递交、聚合卡片统计数据的展示（总数、成功、失败、命中缓存）、以及按条件搜索与展示最新视频任务记录的列表查询功能。
- **`web/dashboard.md`**: 用户操作帮助和系统结构概览说明文件。
- **依赖项更新**: 在 `requirements.txt` 追加了 Phase 4 所需的 `fastapi`, `uvicorn`, `pydantic` 等核心模块支持依赖保障。

## 2. 测试执行与验证清单

使用独立校验脚本配合 `uvicorn` 本地节点，对所有的 API 进行端到端的冒烟测试：

| 测试项 | 覆盖范围 | 预期状态 | 实际结果 |
|-------|---------|----------|----------|
| API: `GET /api/runs` | 表结构兼容性、查询分页与复合展示逻辑 | 返回 HTTP 200 结果体 | ✅ HTTP 200 OK |
| API: `GET /api/stats` | SQL 聚合计数与 Dashboard 状态指标读取对应 | 返回 HTTP 200 体现各类状态计数 | ✅ HTTP 200 OK |
| 页面: `GET /dashboard` | Web 静态 HTML 模板分发与挂载检查 | 返回 HTTP 200 | ✅ HTTP 200 OK |
| API: `POST /api/jobs/playlist` | 子进程任务开启，通过 Pydantic 过滤提交体与 SQLite 入库写入 | 给予即时队列接收响应且反馈 job_id | ✅ 提交任务接受，响应排队成功 |
| 生命周期: Pipeline 完整 | Pipeline 结束后回写执行轨迹或报错，联动调用 ZIP 组件触发合并打包，修改主状态 | 通过轮询 API 能够捕捉到目标 ZIP 包和 Finish 标志 | ✅ Job 回传 Completed，输出 summary_bundle*.zip 报表文件并提供下载锚点 |

验证结论：Phase 4 Dashboard 与 ZIP 组件链路完全通畅，新增代码完美融合进基础项目中，可以投入后续的交付环节。

## 3. 防范漏洞与后续建议

1. **内网映射 / 挂网防御**: 若外网正式上线暴露需要补齐 Uvicorn Nginx 反代并套用基于请求防洪、及账号凭夹如 Basic Auth 验证手段。  
2. **Key 生命周期追踪**: 当前方案中前台输入的调用 API Key 直接以环境变量临时封装注入到调用的 Popen 虚拟 Shell 中，未明文暂存落地硬盘以保障秘钥高度机密，通过合规安全点检查校验。

## 4. Phase 4 使用指南 (How to use)

### 4.1 如何启动 Dashboard Web 面板

1. **激活虚拟环境与依赖项**（确保 `fastapi` 和 `uvicorn` 等库已安装）：
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. **启动 Dashboard 界面**：
   在仓库根目录直接运行提供的快捷脚本（脚本内部会自动拉起 uvicorn 和激活环境）：
   ```bash
   ./start_dashboard.sh
   ```
3. **在浏览器中访问**：
   打开浏览器并访问：[http://127.0.0.1:8999/dashboard](http://127.0.0.1:8999/dashboard)

### 4.2 如何使用 Phase 4 仪表盘功能

* **实时监控数据卡片**：顶部四张卡片分别展示 Total Processed、Completed、Failed 和 Reused (代表命中了缓存)。这些均由后台数据库(`run_track.db`)即时测算而出。
* **提交新任务 (Submit New Job)**：
  1. 在 `Playlist/Video URL` 栏填入一个 YouTube/Podcast 播放列表链接 或 单一链接。
  2. 点击 **Start Processing** 获取后台列队派发的 `Job ID`。
  3. 后端服务此时将通过 `job_manager.py` 挂起一条异步任务调起 `src/main.py -list "<URL>"` 生成摘要文件。
* **查阅近期任务 (Recent Runs)**：
  1. 下方表格列出了历史处理流程（比如识别的 UP 主名/标题等 Identifier、跑的类型，以及对应的成功/错误代码）。
  2. 提供一个简单的搜素条可检索相关运行记录。
* **结果下载与 ZIP 导出**：
  当一个前端触发建立的 Playlist 任务跑完时，系统会把它本次生成所有的 Markdown Summary / Transcript 文件和清单聚合，在 `output/zips/` 目录产生一份形如 `summary_bundle_job_xxx_YYYYMMDD_HHMM.zip` 的报告打包档案。您亦可通过 API `GET /api/jobs/{job_id}/zip` 对其进行远端拿取。

### 4.3 补充功能：精准的 Daily Digest 报告
通过本次升级，现每日报告(Daily Summary)已优化为更智能的匹配方式。只需执行：
```bash
python src/main.py --daily-summary
```
系统将会读取最新的 .md Markdown文件头匹配最原始的 YouTube 标题和 AI 推理核心，并推算纯粹的 Uploader 名称。随后，此 Daily Digest 将自动置于仓库根部的 `daily_digest/` 目录下（便于在 GitHub 直观审阅）。
