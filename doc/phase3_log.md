# Phase 3 Log: DB扩展与高级工作流

## 目标完成情况
根据 `antigravity_action_plan_20250319.md` 文件中 Phase 3 的规划，我们已全部完成系统重构测试和功能扩展。主要涵盖两大领域的增强：文件系统及工作流增强、策略增强与高阶工作流（特别是 YouTube 动态监控）。

## 核心实现
### 1. File Storage 及历史复用模型
*   **Database Schema 升级:** 在 `src/run_tracker.py` 中新设了 `file_storage` 表，用以精细追踪每个 Run 下生成的文件（Transcript / Summary / Report / Audio），支持软删除(soft delete)。同时也关联了 `github_url` 字段以便追踪上传后的 URL 链接。
*   **文件重命名体系 (`utils.py` / `summarizer.py` / `github_handler.py`):**
    *   重构 `create_report_filename` ，新增 `upload_date` 支持。格式设定为 `{upload_date}_{uploader}_{video_title}.md`。
    *   `src/github_handler.py` 中的 `upload_to_github` 更新，支持接受 `uploader` 字段并将文件归档至 `reports/{uploader}/{YYYY_MM}/` 目录；引入 `use_month_folder` 控制是否启用月度存档，提升 GitHub 组织可读性。
*   **重复处理与复用机制 (`pipeline.py`):** 添加 `find_latest_completed_report` 在 pipeline.py 内各个入口方法 (`run_youtube`, `run_local_mp3`, `run_podcast`) 做拦截。命中的场景直接标记状态为 `REUSED_EXISTING_REPORT`，返回先前的 `report_file`。

### 2. 动态提示词与环境增强
*   **UP主元信息收集:** 引入 `_upload_info_json()` 来读取提取的 `video_info` 详情并落盘为 `info.json` 再上传至对应的 GitHub 目录。
*   **自定义 Prompt 策略 (`prompt_selector.py`):** 新增 `PromptSelector` 类和对应的配置规则：
    *   支持基于 CSV 映射字典 (`config/prompt_profile_map.csv`) 为特定频道定制不同的提示词模型类型。
    *   支持定义具体的提取模型 (`config/prompt_types/` 内如 `talk.txt`, `education.txt` 等)。
    *   与 `Summarizer` 直接贯通使得生成的 Prompt 信息能够被自动关联并在 `runs` 表中留档追溯 (`prompt_type`, `prompt_source`, `prompt_index`, `prompt_file`)。

### 3. 定时 YouTube 监控系统与日更报表
*   **Channel Watcher (`src/channel_watcher.py`):** 基于 `yt-dlp` 以 `extract_flat=True` 提取策略对频道近 15 个视频执行监测，并将未完成/最新（比对 `last_seen_upload_date`）的直接加入流水线。包含导入监听配置、定期清理及全增量追踪（存储在 `watch_channels`，`watch_channel_state`），并且完全记录每次 Scan 的 `watch_scan_runs`。
*   **日度 Summary (`src/daily_summary.py`):** 按日期为触发将所有今天标记为完结的视频/博客内容提取组合成单 Markdown `reports/daily_summary/YYYY_MM/YYYY-MM-DD.md` 报告。
*   **Main CLI (`src/main.py`) 的全面兼容:** 加入了五类针对 watcher 的专属扩展命令 `--import-watchlist`, `--list-watch-channels`, `--watch-run-once`, `--watch-daemon` 以及 `--daily-summary` 以便轻松触发守护进程。并新增 `bash/watch-run.sh` 作为守护进程启动快捷脚本。

## 单元测试与验证结果
全部验证完毕并无错误 (Exit Code: 0)：
1.  **`tests/test_file_storage.py`:** CRUD 通过。
2.  **`tests/test_prompt_selector.py`:** 映射与 Selector 回退（Fallback）功能通过。
3.  **内联代码格式化执行:** `python -c "from src.utils import create_report_filename..."` 验证：`20260315_UP主_Title.md` 返回名称符合预期。
