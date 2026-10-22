# 01: 范围裁剪 + info_json 删除

**What to build:** 把 repo 砍到只剩 YouTube 主链：删 dashboard 全套、podcast 输入、`batch_processor.py`（留 `batch.py`）、博主 `info_*.json` 生成逻辑；删完后 `-video / -list / -local` 三入口仍可跑，测试套件恢复全绿。

**Blocked by:** None（可立即开工）。

**Status:** ready-for-agent

- [ ] Dashboard 相关（app / job / service / exporter / web / sh）删除，CLI 不再引用
- [ ] Podcast 相关输入与测试删除，本地 MP3 输入保留
- [ ] 未被调用的泛型批处理器删除，playlist 编排保留（含共享 Transcriber 预热）
- [ ] 每次跑完写 `info_<博主>.json` 并上传的逻辑删除（含两处调用），以后不再生成；提示词 CSV 保留
- [ ] 顺手删坏的 `begin_transaction` 空转方法与 `utils.basicConfig` 重复日志配置（ponytail：不做 logger 系统重构，`setup_logging` 只做幂等一行）
- [ ] 同步删改测试，`python -m unittest discover tests` 全绿；codegraph 查无残留引用（无 orphan import）
