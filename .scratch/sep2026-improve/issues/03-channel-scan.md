# 03: channel 扫描修复 + channellist.txt

**What to build:** 给定 root 的 channel 清单能扫出“最近 2 天的新视频”，失败的不自动重跑，为定时打下输入基础。

**Blocked by:** 02 新去重库 + 迁移 + 本地 hash + --force。

**Status:** ready-for-agent

- [ ] root `channellist.txt`：一行一个 channel URL，跳空行和 `#` 注释
- [ ] `--scan channellist.txt` 只取 `published` 最近 2 天（拿不到日期算旧不跑；`upload_date` 缺失回退 `published_parsed`）
- [ ] 新视频判定：以新库 COMPLETED 为准 + 游标截断；FAILED 单独列出不自动重跑
- [ ] 修 N+1 连接（复用一次）、对齐共享 Transcriber 预热、去掉写死的抓取条数；裸 `sqlite3.connect` 顺手收敛到 `DatabaseManager`（不单开全仓重构票）
