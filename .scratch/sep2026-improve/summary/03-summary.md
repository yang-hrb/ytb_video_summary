# 03-summary：channel 扫描修复 + channellist.txt + --scan

## 做了什么

按 `issues/03-channel-scan.md` checklist 与 spec §5，把 channel 扫描切到"扫 TXT →
查新库 → 只跑近 2 天没 COMPLETED 的"语义，并修掉 `execute_scan` 的四个已知坑
（游标 break 永不触发、`playlistend=15` 写死、逐视频 N+1 连接、无 Transcriber
预热）。未提交 git。

## 改了什么代码

- `src/channel_watcher.py`（重写扫描路径，保留类名/旧 watch 方法签名兼容）：
  - 新增 `read_channellist(path)`：跳空行和 `#` 注释（含行首空格的缩进注释，
    旧 `import_watchlist` 用未 strip 行判断是个小 bug，一并修掉）；文件不存在
    则写示例文件并返回 `[]`。
  - 新增 `entry_publish_date(entry)`：`upload_date` → `timestamp` →
    `published_parsed` 回退，拿不到返回 `None`（算旧不跑）。
  - 新增 `is_recent(entry, cutoff)` / `select_scan_videos(entries, status_of,
    cutoff)`：新est-first 遍历，首个 COMPLETED 截断游标（修旧代码
    `if not row ... elif vid == last_vid: break` 永不 break 的 bug），首个
    旧/无日期条目截断，FAILED 只收集不跑。
  - `fetch_channel_entries(channel_url, cutoff)`：`extract_flat` 保留，
    `playlistend=15` 删除，改传 `dateafter=<cutoff YYYYMMDD>`；客户端
    `is_recent` 做第二道过滤。
  - `execute_scan(channels_file=None, upload=True, summary_style="detailed")`：
    有 `channels_file` 则直读 TXT；无则回退旧 `watch_channels` 表（daemon 兼容）。
    去重库只开一次（`get_dedup_db()`），每 channel 一条
    `SELECT video_id, status ... WHERE video_id IN (...)`（N+1 消除）；
    Transcriber 经 `src.batch._make_shared_transcriber()` 预热一次（对齐
    batch.py，失败则降级 `None` 由 pipeline 懒加载）；全文件零
    `sqlite3.connect`，旧 watch/scan_runs 表读写走 `self.tracker.db`
    （`DatabaseManager`）。
- `src/cli/parser.py`：互斥输入组新增 `--scan FILE` + epilog 示例。
- `src/cli/commands.py`：dispatch 新增 `_handle_scan`（透传 cookies/browser/
  style/upload），`_show_usage` 补 `--scan` 行。
- `channellist.txt`（新增，root）：全注释示例文件，用户手维护。
- `tests/test_channel_scan.py`（新增，13 tests）：channellist 解析/缺失创建、
  日期三级回退 + 无日期算旧、`select_scan_videos` 四条语义（COMPLETED 截断 /
  FAILED 单列 / 旧截断 / 无日期截断）、`execute_scan` 端到端（fake entries +
  temp dedup DB + mock Pipeline：只跑 `fresh1`，`bad1` 列出不跑，`done1` 截断
  后续，Digest 被调用）、`--scan` 在 help 可见。

## 扫描语义

扫 TXT → `fetch_channel_entries`（dateafter=今-2天）→ 新库批量查状态 →
`select_scan_videos`（COMPLETED 截断 + 2 天窗口 + FAILED 单列不重跑）→
倒序（先旧后新）跑 pipeline → `generate_daily_summary(upload)` 照发。
FAILED 视频：仅 `logger.warning` 列出，下次扫描仍列出、不自动跑。

## 测试命令 + 结果

- `python -m unittest tests.test_channel_scan` → Ran 13 tests, OK
- `python -m unittest discover tests` → **Ran 63 tests, OK**（50 原有 + 13 新增）
- `python src/main.py --help` → `--scan FILE` 在 usage/options/epilog 可见
- `grep sqlite3.connect|playlistend src/channel_watcher.py` → 零命中
- 未做真跑验证（需网络 + OPENROUTER key，留给 spec §9 步骤 5 手跑环节）

## 风险 / 下一步

- 旧 `watch_*` 表仍在 `--scan` 无参/daemon 路径读写旧库（有意保留兼容，全量
  下线留给 issue 05 `--max-hours` 那步；`--scan FILE` 主路径已零读旧 runs 表）。
- `dateafter` 对 flat `/videos` 提取若被 yt-dlp 忽略，客户端 `is_recent` +
  遇旧截断仍保证语义正确，只是多拉几页（`entries` 遍历遇到旧条目即停）。
- `execute_scan` 仍返回 `int`（processed 数），FAILED 详情只打 log；Digest
  红区/复用引用是 issue 06（daily_summary）范围，本步不动。
- `channellist.txt` 为 untracked 新文件，随本 issue 一起提交即可。
