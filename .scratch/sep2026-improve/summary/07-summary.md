# 07-summary：AGENTS.md 重写 + 四命令验收（mock 冒烟）

## 做了什么

按 `issues/07-agent-docs.md` 与 spec §7/§9，只重写 `AGENTS.md`（无新增 SKILL.md，无代码改动，未提交 git）。
重写前读完 01–06 summary + `git status/diff --stat` 确认全貌（01–06 共 27 files changed, +931/−1856）。

## AGENTS.md 结构（重写后 7 节，求准不求长）

1. **Setup** — `venv/` 路径（`python -m venv venv && source venv/bin/activate`）、`.env` 经 `config/settings.py:load_dotenv()` 读取、`OPENROUTER_API_KEY` 缺失则所有 CLI exit 1。
2. **The four commands** — `-video / -list / --scan / -local` 四条全带规范 flags（`--style detailed --cookies cookies.txt --upload`，对齐 `full_auto_run_playlist.sh:167` 的 `-list … --style detailed $cookies_param $upload_param`）；`-local` 给文件夹示例 `./audio_files`；`--scan` 注 2 天窗口 + `scripts/daily_scan.sh` cron（`0 4 * * *`、`--max-hours 4`、`logs/scan.lock`）；`--force/--no-reuse`、`--help`。
3. **Dedup DB** — `logs/ytb_summary_track.db` 单表 `videos` 全 14 列 DDL（含 04 新增 `uploader/title/duration_seconds`）、`local_<sha256[:16]>`（前 8MB+大小）语义、COMPLETED 零新增复用、旧库冻结备份 + 自动迁移。
4. **Failures** — `logs/two_time_fail.txt` CSV 五字段格式 + Digest 顶部 `🔴 Failures`（`fail_count>=2`）及下三段 + `PENDING_KILLED` 下次静默重跑。
5. **yt-dlp 手动升级句** — 1–2 个月手动 `pip install -U yt-dlp`，跑通 1 个 playlist 验证后锁版本进 `requirements.txt`，排障先 `yt-dlp --version`。
6. **Architecture** — pipeline / execute_scan（含 `select_scan_videos` 截断语义）/ summarizer（60000 截断 + waterfall + 401/403）/ run_tracker / prompts / GitHub 路径（`summary/<N_X_letter>/<uploader>/YYYY_MM`，pipeline 传 `use_category_folder=True` 已核实）/ 输出目录 / 异常与日志。
7. **Testing** — `discover tests`（84）+ 单模块示例；声明无真实网络调用、无 dashboard/uvicorn。

文档中断言逐条对代码核实过：`SCAN_LOCK_NAME="scan.lock"`、`select_scan_videos`、`_make_shared_transcriber`、`generate_daily_summary`、`MAX_TRANSCRIPT_CHARS=60000`、`REPORT_DIR`、`get_category_folder` 均存在且语义如所述。

## 四条 CLI 验证（全部通过）

- `python src/main.py --help` → usage 行含 `-video URL | -list URL | -local PATH | --batch FILE | --scan FILE`，`--style` 默认 `detailed`、`--cookies-from-browser` 默认 disabled、`--force/--no-reuse/--max-hours/--upload` 均可见。
- argparse 四命令解析冒烟（`create_parser().parse_args`）：`-video/-list/--style detailed/--cookies/--upload` OK、`-list` OK、`-local ./audio_files` OK、`--scan channellist.txt --max-hours 4` → `4.0` OK。

## 测试 + 结果

- `python -m unittest discover tests` → **Ran 84 tests, OK**（与 06 交付数一致，AGENTS.md 为纯文档改动）。
- 另 `test_scan_timeout` 内已有 `--scan --max-hours --upload` 真 Digest 落盘 + mock GitHub 全链冒烟（05 留下，本步未重跑单模块，discover 全绿已覆盖）。

## 真实 vs mock 说明（诚实记录）

- **真实跑**：`--help`、argparse 四命令解析、84 单测（含 mock `requests.post` / fake pipeline / temp DB）。
- **Mock 代替真实上传**：1×`-video` + 1×小`-list` + 1×`-local` 文件夹 + 1×channel `--scan` 的真实端到端**本次未跑**——本机无 `venv/`、无 `.env`（无 `OPENROUTER_API_KEY`，按设计所有 CLI 直接 exit 1）、无 `cookies.txt`；spec §9 步骤 5 的手跑留给有 key + 网络的 Hermes 主会话。 burglar 现场 `yt-dlp` 为 2026.01.29 可用。
- Hermes 主会话真实验收时：先建 venv + `.env`（`OPENROUTER_API_KEY` 必填，`--upload` 另需 `GITHUB_TOKEN/REPO`），照 AGENTS.md 第二节四条命令逐条跑即可。

## 残留风险

- `requirements.txt` 中 `yt-dlp>=2024.10.0` 为下限非锁版本——符合 spec §2.3（锁版本发生在下次手动升级验证后），AGENTS.md 已写明流程。
- `--status/--list-failed` 等诊断命令仍读旧库（02–05 有意遗留，未在 AGENTS.md 中宣传，避免教错）。
- `channellist.txt`、`scripts/daily_scan.sh`、5 个新测试文件均为 untracked，随 01–06 改动一起提交即可（本步未 commit，按约束）。
