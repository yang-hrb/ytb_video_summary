# 06: 摘要保命（截断 + 瀑布报错）

**What to build:** 超长视频不再把 prompt 撑爆 400 就全灭：保命截断 + 换模型重试 + 失败原因可查。

**Blocked by:** 01 范围裁剪 + info_json 删除（与 02–05 可并行）。

**Status:** ready-for-agent

- [ ] transcript 按字符/Token 上限截断（`transcript[:N]` 保命 5 行，禁 map-reduce 分块，禁新建错误聚合类）
- [ ] waterfall 收集每个模型的失败原因拼串抛出（不再是裸 `All models failed`）
- [ ] 400 细分：模型不存在/无效换下一个，仅 401/403 鉴权类直接停
