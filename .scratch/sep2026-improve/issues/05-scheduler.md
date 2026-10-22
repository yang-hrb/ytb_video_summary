# 05: 定时 Runner + --max-hours 内部超时

**What to build:** 每天 04:00 一次全自动：扫清单 → 查库 → 跑 pipeline → 发 Digest → 传 GitHub；4 小时到点自己停，半成品 Digest 照发。

**Blocked by:** 03 channel 扫描修复、04 Digest 跨天修复。

**Status:** ready-for-agent

- [ ] `--scan` + `--max-hours 4` 代码内计时停（`time.monotonic`  deadline，禁 APScheduler/新调度库；不用系统 timeout，保证能发半成品 Digest）
- [ ] 超时算“没跑过”：`fail_count` 不加，`status=PENDING_KILLED`，下次静默重跑，Digest 里标出来
- [ ] crontab 每天 04:00 可配（含 venv 激活、`.env` 读取、防重叠 lock 用 stdlib `Path` 锁文件一行，不引新库）
- [ ] 全链冒烟：1 个 channel → 新视频 → Digest → GitHub
