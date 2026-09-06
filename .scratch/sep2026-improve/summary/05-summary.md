# 05-summary：--max-hours 内部超时 + scan 锁 + 定时脚本

## 做了什么

按 `issues/05-scheduler.md` checklist 与 spec §5，给 `--scan` 加代码内计时停与单实例锁，
并提供每天 04:00 的 crontab 配置。超时算"没跑过"（与 04 约定的 `PENDING_KILLED` 语义一致），
半成品 Digest 照发。未提交 git。

## 改了什么代码

- `src/channel_watcher.py`：
  - `execute_scan(..., max_hours=None)`：`deadline = time.monotonic() + max_hours*3600`；
    每个视频派发前检查，命中则把当前及剩余队列标 `PENDING_KILLED` 并跳出外层 channel 循环；
    `run_results` 新增 `'pending'` 键透传 Digest（缺省老调用方走 DB 回退，不受影响）。
  - `_mark_pending_killed()`：经 04 的 `mark_video_pending_killed` 落库（`fail_count` 不加，
    不覆盖 COMPLETED），收集行供 Digest `Unprocessed` 段。
  - `acquire_scan_lock()`：stdlib `Path.touch(exist_ok=False)` 锁文件（`logs/scan.lock`），
    6 小时以上视为 stale 回收；返回 path 或 None。零新依赖。
- `src/cli/parser.py`：新增 `--max-hours HOURS`（float）+ epilog 示例。
- `src/cli/commands.py`：`_handle_scan` 先拿锁（被占则 warning 跳过，不报错），透传 `max_hours`，
  finally 删锁。
- `scripts/daily_scan.sh`（新增，可执行）：cd root → 激活 venv → 读 `.env` → 有 cookies.txt 才带
  `--cookies` → `python src/main.py --scan channellist.txt --style detailed --upload --max-hours 4`
  （对齐默认 detailed+cookies+upload）。文件头含 crontab 行与手跑说明。
- `tests/test_scan_timeout.py`（新增，8 tests）：见下。

## 超时语义

- 超时 ≠ 失败：`status=PENDING_KILLED`，`fail_count` 不加，不写 `two_time_fail.txt`。
- 下次扫描静默重跑：`select_scan_videos` 只认 COMPLETED 截断 / FAILED 跳过，
  PENDING_KILLED 照常进入 `to_process`（有单测锁定）。
- Digest `Unprocessed` 段经 `run_results['pending']` 精确列出本次被杀的；`--daily-summary`
  手跑时回退全表查询（04 逻辑不变）。

## crontab 配置

```
0 4 * * * /Users/yangyu/github/ytb_video_summary-Sep/scripts/daily_scan.sh >> /Users/yangyu/github/ytb_video_summary-Sep/logs/cron.log 2>&1
```

venv 激活、`.env` 读取、防重叠锁全在链内；路径按本机替换。重叠时本次直接跳过（warning），
不杀旧进程、不报错退出。

## 测试命令 + 结果

- `python -m unittest tests.test_scan_timeout` → Ran 8 tests, OK（0 预算全杀 / 部分超时先跑后杀 /
  PENDING_KILLED 下次重选 / 无预算原语义 / 锁互斥+释放 / stale 锁回收 / help 可见 /
  全链冒烟：fake pipeline 落 COMPLETED → 真 Digest 落盘含标题 → GitHubHandler.upload_file 被调一次）
- `python -m unittest discover tests` → **Ran 78 tests, OK**（70 原有 + 8 新增）
- `python src/main.py --help` → `--max-hours HOURS` 可见；imports OK
- 无真跑验证（需网络 + OPENROUTER key；冒烟已用 fake pipeline + mock GitHub 覆盖
  `--scan --max-hours --upload` 整链）

## 风险 / 下一步

- `time.monotonic` deadline 只在"派发新视频"处检查：单个视频 pipeline 本身超长时，
  实际结束时间会超过预算（有意为之：不中断在跑视频，保证半成品 Digest 能发）。
- 未 fetch 的后续 channel 在超时后直接跳过、不落 PENDING_KILLED（视频 id 未知，无法标记）；
  下次扫描照常发现它们。
- kill -9 会留 stale 锁，最长 6 小时后自愈；急需可手删 `logs/scan.lock`。
- `_post_process` 在 `--upload` 后会再发一次当日 Digest（同文件覆盖写，无害；AGENTS 重写时可提一句）。
