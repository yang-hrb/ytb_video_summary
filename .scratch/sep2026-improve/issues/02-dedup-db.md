# 02: 新去重库 + 迁移 + 本地 hash + --force

**What to build:** 以新去重库为唯一口径：YouTube 按 video_id、本地 MP3 按内容 hash 去重；已 COMPLETED 的直接复用旧 MD（GitHub 零新增），`--force` 可强制重跑并让跳过可见。

**Blocked by:** 01 范围裁剪 + info_json 删除。

**Status:** ready-for-agent

- [ ] 新库 `logs/ytb_summary_track.db` 建单表 `videos(video_id PK, url, channel_url, publish_date, first_seen, md_path, github_url, status, fail_count, last_error, updated_at)`（决策来自 grill，见 spec §4）；读写复用现有 `DatabaseManager`，不写新 wrapper
- [ ] 状态口径只用一个 `FAILED_STATUSES` tuple 常量，不建 `RunStatus(Enum)`（ponytail：单实现抽象不加）
- [ ] 旧库改名备份并按新格式一次性导入 COMPLETED（冷启动不重烧钱）；迁移后确认旧库无人再写
- [ ] 本地 MP3 主键 = `local_<sha256(内容)[:16]>`（stdlib `hashlib`，禁随机 UUID；大文件可限读前 N MB + 文件大小拼算），`url` 存原始路径；改名不重跑、改内容才重跑
- [ ] pipeline（含 `-local`）跑前先查新库，命中则 Digest 贴旧 MD 路径引用、不调下载/转录/摘要
- [ ] 新增 `--force / --no-reuse`，复用时打印报告路径 + 生成时间
