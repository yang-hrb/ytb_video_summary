# 07: AGENTS.md 重写 + 端到端验收

**What to build:** Hermes Agent 照文档就能跑四条命令，小 playlist 全链跑通并上传 GitHub。

**Blocked by:** 05 定时 Runner、06 摘要保命（05 已隐含 02–04）。

**Status:** ready-for-agent

- [ ] 只重写 `AGENTS.md`，禁新增 `SKILL.md` 双文档：venv、`.env`、四条 CLI（`-video / -list / --scan / -local`）、新库表结构、失败看 `logs/two_time_fail.txt` + Digest 红区、yt-dlp 手动升级句
- [ ] 与旧 `full_auto_run_playlist.sh` 流程对齐（默认 detailed + cookies.txt + upload）
- [ ] 验收：1 个 `-video` + 1 个小 `-list` + 1 个 `-local` 文件夹 + 1 个 channel 的 `--scan` 全绿并上传
