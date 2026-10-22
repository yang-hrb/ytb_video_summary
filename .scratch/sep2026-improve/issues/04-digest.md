# 04: Digest 跨天修复 + 红区 + two_time_fail

**What to build:** 跨天跑也只出一份以启动日为准的 Daily Digest：新增/复用/失败红区/未跑四段齐全，两次失败置顶标红并落盘。

**Blocked by:** 02 新去重库 + 迁移 + 本地 hash + --force（与 03 可并行）。

**Status:** ready-for-agent

- [ ] Digest 日期 = 启动日（04:00 那次），超时跑到第二天也归同一份
- [ ] 四段式：本次新增 / 复用引用（旧 MD 路径） / 顶部红区 / 未跑 `PENDING_KILLED`
- [ ] `fail_count=2` 写 `logs/two_time_fail.txt(video_id,url,第一次,第二次,错误)`（stdlib csv 写一行）+ Digest 顶部标红 + 原因
- [ ] 改读新库列，不再靠文件名猜 uploader；修总时长恒 0；裸 `sqlite3.connect` 顺手收敛到 `DatabaseManager`
