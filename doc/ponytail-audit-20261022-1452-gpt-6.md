# Ponytail 全仓库简化审计

- 审计时间：2026-10-22 14:52 CDT
- 范围：全仓 Python 模块、配置、依赖、测试和 shell 脚本；仅记录复杂度与可删减项，不评估正确性、安全性或性能。
- 依据：CodeGraph 调用关系及全仓引用检索；未修改代码，也未运行测试。

## Findings（按预计删减量排序）

1. `shrink:` 将根目录的 `full_auto_run_playlist.sh` 收缩为调用 `scripts/full_auto_run_playlist.sh` 的薄入口，后者已提供跨平台虚拟环境路径；两份脚本约 192/195 行，根脚本改为约 2 行可省约 190 行。[full_auto_run_playlist.sh:1](../full_auto_run_playlist.sh) · [scripts/full_auto_run_playlist.sh:1](../scripts/full_auto_run_playlist.sh)
2. `delete:` 删除无生产调用者的 `file_storage` 表创建、五个读写方法及仅覆盖这些方法的测试；生产流程已通过 `runs` 记录产物路径，现有引用只出现在测试和一条注释中，预计省约 140 行。[src/run_tracker.py:352](../src/run_tracker.py) · [src/run_tracker.py:603](../src/run_tracker.py) · [tests/test_file_storage.py:1](../tests/test_file_storage.py)
3. `delete:` 移除当前没有导入或实例化的应用异常类型及通用基类，只保留 `DatabaseError`；可将它直接继承 `Exception`，并在数据库包装处用 `raise ... from e` 保留原始异常链，预计省约 75 行。[src/exceptions.py:11](../src/exceptions.py) · [src/database.py:50](../src/database.py)
4. `delete:` 移除未被代码读取的 `BROWSER_TYPE`、`USE_COOKIES_FILE` 配置及 `.env.example` 条目；当前 cookie 行为由 CLI 参数控制，预计省约 6 行。[config/settings.py:47](../config/settings.py) · [.env.example:41](../.env.example)

net: -411 lines, -0 deps possible.
