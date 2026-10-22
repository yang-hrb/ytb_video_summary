# 04-summary：Digest 跨天 + 四段式 + two_time_fail

## 做了什么

按 `issues/04-digest.md` checklist 与 spec §6，把 Digest 切到"启动日一份、四段齐全、两次失败标红落盘"语义，并修掉 `daily_summary` 的两个已知坑（`duration` 恒 0、文件名 `split('_')` 猜 uploader）。未提交 git。

## 改了什么代码

- `src/run_tracker.py`：
  - `videos` 表新增 `uploader / title / duration_seconds` 三列（DDL + `init_videos_table` 内 `PRAGMA` 探测缺列 `ALTER`，存量库自动迁移；更新了 `test_dedup` 的 schema 断言）。
  - `mark_video_completed` 新增 `uploader/title/duration_seconds` 参数并写入。
  - `mark_video_failed` 改为返回新 `fail_count`；`==2` 时用 stdlib `csv` 向 `logs/two_time_fail.txt` 追加一行 `video_id,url,第一次失败时间,第二次失败时间,错误`（第一次取更新前的 `updated_at`）。
  - 新增 `mark_video_pending_killed`（`fail_count` 不加；`WHERE status != 'COMPLETED'` 防晚到完成被覆盖，供 05 `--max-hours` 用）+ `TWO_TIME_FAIL_NAME` 常量 + `two_time_fail_path()`。
- `src/pipeline.py`：`_complete` 透传三字段；`run_youtube` / `run_local_mp3` 从各自 `video_info` 传入（`duration`/`uploader`/`title`）。
- `src/daily_summary.py`（重写主体，删文件名猜测 + MD 正文解析 + 裸 `sqlite3.connect`）：
  - 签名 `generate_daily_summary(target_date=None, upload=True, run_results=None, db=None)`；日期即启动日，文件名 `{day}.md`（同启动日覆盖写一份，跨天不散写）。
  - 四段：`🔴 Failures`（DB `FAILED fail_count>=2` + 原因）/ `New Reports` / `Reused References` / `Unprocessed (PENDING_KILLED)`；统计行含新增数/复用数/未跑数 + 新增总时长（`duration_seconds` 求和，修恒 0）。
  - `run_results={'new','reused','pending'}` 由 scan 传入；缺省时 `new` 按 `date(updated_at)=day` 查库、`pending` 查全表（`--daily-summary` 手跑可用）。
  - DB 经 `DatabaseManager`（注入或 `get_dedup_db()`），全文件零 `sqlite3.connect`。
- `src/channel_watcher.py`：`execute_scan` 开头记 `digest_date` 并透传 `target_date`；循环内按 `res.get('reused')` 把 DB 行分拣进 `new_now / reused_now`，扫完传 `run_results` 给 Digest。
- `tests/test_digest.py`（新增，7 tests）：two_time csv 一行五字段 + 第二次才落盘；`PENDING_KILLED` 不加 fail_count、不覆盖 COMPLETED；四段 header + 列直读 + `1h 1m 1s` 总时长；跨天文件名/标题归启动日；standalone 按日期查库；全空返回 None。

## Digest 结构

```
# Daily Summary for 2026-09-05
## 🔴 Failures (fail_count ≥ 2)   ← bad1 + err2
## Statistics                       ← 新增/复用/未跑数 + 新增总时长
## New Reports                      ← uploader | title | Report 链接
## Reused References                ← 旧 MD 路径引用，零新增
## Unprocessed                      ← PENDING_KILLED，下次静默重跑
```

## 测试命令 + 结果

- `python -m unittest tests.test_digest tests.test_dedup` → Ran 23 tests, OK
- `python -m unittest discover tests` → **Ran 70 tests, OK**（63 原有 + 7 新增）
- `grep sqlite3 src/daily_summary.py src/channel_watcher.py` → 零命中；四模块 imports OK
- 未做真跑验证（需网络 + OPENROUTER key，留给 spec §9 步骤 5 手跑环节）

## 风险 / 下一步

- `fail_count` 语义与 02 一致：`mark_video_failed` 唯一加计数点；`PENDING_KILLED` 永不加（与 05 约定）。
- 红区目前只收 `fail_count>=2` 的 FAILED 行；`two_time_fail.txt` 是"第 2 次当时"追加，若用户手删 DB 行后重跑，计数从 1 起（与 02 幂等 `INSERT OR IGNORE` 语义一致，可接受）。
- `--daily-summary` standalone 手跑时 `Reused` 段恒 `(none)`（复用只在 scan 上下文可知）；`--status/--list-failed` 仍读旧库，05 统一处理。
- Digest 上传路径沿用旧逻辑（需 `GITHUB_TOKEN/REPO`，否则本地落盘返回路径）。
