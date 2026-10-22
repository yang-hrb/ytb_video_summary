# 02-summary：新去重库 + 迁移 + 本地 hash + --force

## 做了什么

按 `issues/02-dedup-db.md` checklist 与 spec §4/§7/§9，把"做没做过"的口径切到新库
`logs/ytb_summary_track.db` 单表 `videos`：YouTube 按 `video_id`、本地 MP3 按内容 hash
去重；命中 COMPLETED 直接复用旧 MD（零下载/转录/摘要，GitHub 零新增）；`--force /
--no-reuse` 可强制重跑；旧库改名备份并一次性导入 COMPLETED。未提交 git。

## 改了什么代码

- `src/run_tracker.py`（+220 行内含全部新逻辑，无新 wrapper 类，复用 `DatabaseManager`）：
  - `FAILED_STATUSES` tuple 常量（唯一状态口径，无 Enum）；`get_failed_runs()` 改用它。
  - 新库常量 `NEW/OLD/BACKUP_TRACK_DB_NAME` + `videos(...)` DDL（spec §4.2 十一列，
    `video_id` PK）。
  - `dedup_db_path / get_dedup_db / init_videos_table / find_completed_video /
    mark_video_completed / mark_video_failed`：COMPLETED 幂等 upsert（`INSERT OR
    IGNORE` 保 `first_seen`）+ FAILED（`fail_count+1`、`last_error`）。
  - `local_content_id()`：`local_<sha256[:16]>`，读前 8MB + 文件大小拼算（大文件便宜），
    改名不重跑、改 1 字节才重跑。
  - `migrate_legacy_db(new/old/backup 可注入)`：旧库存在→改名（含 -wal/-shm）+ 导入；
    都有→导入后删冗余旧文件；只剩备份→仅空表时导入（备份冻结，快路径）；都没有→no-op。
    只导 `status='COMPLETED'`，`INSERT OR IGNORE` 保证可重复跑。
- `src/pipeline.py`：主流程不再写旧库（删 `_start`、`run_id`、`tracker`、
  `find_latest_completed_report` 两处复用、`file_storage` 注册；`resume()`  legacy 保留，
  供历史数据 `--resume-only`）：
  - `__init__` 新增 `force=False`；`run_youtube` 先 `extract_video_id` 再
    `_reuse_hit()`，`run_local_mp3` 先算内容 hash 再查库；命中且 MD 存在→返回
    `{'reused': True, ...}`，不调下载/转录/摘要/上传。
  - 复用时 `logger.info` 打印报告路径 + 文件生成时间（mtime，回退 `updated_at`）。
  - 成功记 COMPLETED（含 `md_path/github_url/upload_date→publish_date`），失败记
    FAILED；DB 不可用时降级继续跑（warning，不崩）。
- `src/batch.py`：`process_playlist_batch / process_local_folder_batch /
  process_batch_file` 新增 `force` 透传；本地批量对 `reused` 结果跳过二次
  `upload_to_github`（GitHub 零新增的关键一行）。
- `src/main.py`：`process_video / process_local_mp3 / process_local_folder /
  process_playlist / process_batch_file` 新增 `force` 透传；本地标题改用文件名 stem
 （hash 只做主键，不污染标题）。
- `src/cli/parser.py`：新增 `--force` + `--no-reuse`（同义）。
- `src/cli/commands.py`：`_force` property（`force or no_reuse`），六个入口全透传。
- `tests/test_dedup.py`（新增，16 tests）：schema 列集合、`FAILED_STATUSES`、
  hash 稳定/改名不变/改内容变、迁移（改名+只导 COMPLETED、幂等、无旧库 no-op）、
  pipeline 复用（stub `process_youtube_video` 断言零调用、`force` 绕过并记 FAILED、
  本地零转录复用、MD 缺失不复用）、flag 解析。

## DB schema（新库单表）

`videos(video_id PK, url, channel_url, publish_date, first_seen, md_path, github_url,
status, fail_count, last_error, updated_at)` — status ∈ {COMPLETED, FAILED}
（`PENDING_KILLED` 留给 issue 05 的 `--max-hours`）。

## 迁移逻辑

首次访问新库（`get_dedup_db()` 默认路径）自动触发 `migrate_legacy_db()`；
本机 `logs/` 下本就没有旧库（01 未产生），走兼容 no-op 已验证。
旧 `runs.report_path/github_url/started_at/updated_at` → 新行；`channel_url/publish_date`
置空（旧表无此列，`PRAGMA` 探测缺列也兼容）。

## 测试命令 + 结果

- `python -m unittest tests.test_dedup` → Ran 16 tests, OK
- `python -m unittest discover tests` → **Ran 50 tests, OK**（34 原有 + 16 新增）
- `python src/main.py --help` → `--force / --no-reuse` 可见
- 未做真跑验证（需 OPENROUTER key + 下载音频，留给 spec §9 步骤 5 手跑环节）

## 风险 / 下一步

- 旧库引用残留（有意不动，属后续 issue 范围）：`RunTracker` 默认路径仍是旧库
  （`--status/--list-failed/--resume-only` 读历史数据）；`github_handler.upload_logs_to_github`
  仍指 `logs/run_track.db`（文件不存在则跳过，后续切新库）；`channel_watcher /
  daily_summary` 仍经 `get_tracker()` 读旧库——spec §5/§6 本就要求后续重写它们读新库、
  Digest 贴复用引用（本 issue 只保证 pipeline 返回 `reused` + 零新增）。
- `channel_watcher.execute_scan` 在 watcher 运行时仍会写旧库 watch_* 表：真正的"旧库零写"
  要等 issue 05 修 watcher；本步已保证 YouTube/local 主流程零写旧库
  （`grep start_run|find_latest_completed_report src/pipeline.py` 零命中主路径）。
- `run_local_mp3` 对 `str` 路径也兼容（`Path(mp3_path).stem`），但调用方均为 Path。
