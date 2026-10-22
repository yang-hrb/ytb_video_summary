# 01-summary：范围裁剪 + info_json 删除

## 做了什么
按 `issues/01-scope-cut.md` checklist 与 spec §2/§3/§9，把 repo 砍到只剩 YouTube 主链：
删除 dashboard 全套、podcast 输入、`batch_processor.py`、博主 `info_*.json` 生成逻辑，
顺手删 `begin_transaction` 空转方法与 `utils.basicConfig` 重复日志配置。`-video / -list / -local`
三入口保留可跑。未提交 git。

## 改了什么代码
- `src/pipeline.py`：删 `_upload_info_json` 定义（原 L149-174）+ 两处调用（`run_youtube`、
  `run_podcast` 内）；删整个 `run_podcast` 方法；类 docstring 去掉 podcast（`run_type` 现为
  `'youtube' | 'local'`）。
- `src/main.py`：删 `apple_podcasts_handler` 导入、`process_apple_podcast` /
  `process_apple_podcast_show` 函数、`process_podcast_show_batch` 导入、`is_apple_podcasts_url` 导入。
- `src/batch.py`：删 `process_podcast_show_batch` 整函数；`process_batch_file` 删 podcast
  分支与相关导入；模块 docstring 去 podcast。
- `src/cli/parser.py`：删 `--apple-podcast-single / --apple-podcast-list` 参数与 epilog
  示例；description 改为 `Supports YouTube and Local MP3`。
- `src/cli/commands.py`：删 dispatch 中 podcast 两分支、`_handle_apple_podcast_single/list`
  方法、`_handle_default_url` 中 podcast 检测分支、usage 中 podcast 两行。
- `src/cli/display.py`：banner `YouTube + Apple Podcasts + Local MP3` → `YouTube + Local MP3`。
- `src/utils.py`：删顶层 `logging.basicConfig(...)`；删 `is_apple_podcasts_url`。
- `src/database.py`：删 `begin_transaction` 空转方法（`with get_connection() as conn: conn.execute("BEGIN")`
  提交即退出，实际无事务语义）。
- `src/logger.py`：`setup_logging` 加一行幂等守卫 `if logger.handlers: return logger`
 （不做 logger 系统重构）。
- `src/exceptions.py`：删零引用的 `PodcastError`。
- `requirements.txt`：删 `feedparser`（仅 podcast 用）、`fastapi / uvicorn / pydantic`
 （仅 dashboard 用）；全 repo grep 确认零导入才删。
- 保留：`channel_watcher.py`、`daily_summary.py`、`github_handler.py`、
  `config/prompt_profile_map.csv + prompt_types/`（spec §2.1/§3 要求）。

## 删除了哪些文件
- `src/dashboard_app.py`、`src/dashboard_service.py`、`src/job_manager.py`、`src/zip_exporter.py`
- `src/apple_podcasts_handler.py`、`src/batch_processor.py`
- `tests/test_dashboard.py`（非 unittest，用 `venv/bin/uvicorn` 起真服务器）、`tests/test_batch_processor.py`
- `dashboard.sh`、`web/dashboard.html`、`web/dashboard.md`（`web/` 目录已空删除）

## 测试
- `python -m unittest discover tests` → **Ran 34 tests, OK**（原来 41 个含已删的 2 个文件；
  其余 7 个差值为 `test_dashboard.py` 本就无 TestCase，discover 不计数）。
- `python src/main.py --help` → 输入组仅剩 `-video | -list | -local | --batch`，无 podcast 残留。
- `python -c "import src.main, src.batch, src.pipeline, src.cli.commands, ..."` → imports OK。
- grep（`src/` + `tests/`）：`dashboard|job_manager|dashboard_service|zip_exporter|apple_podcast|
  BatchProcessor|batch_processor|_upload_info_json|is_apple_podcasts_url|begin_transaction|
  basicConfig|run_podcast|process_apple|process_podcast_show|PodcastError|podcasts.apple` → **零命中**。
- 未做真跑验证（需 OPENROUTER key + 下载音频，留给 issue 01 §9 步骤 5 手跑环节）。

## 残留风险 / 下一步建议
- `AGENTS.md` / `README.md` / `doc/` 仍含 dashboard/podcast 描述（有意不动：spec §7 把
  AGENTS 重写划给后续 issue，避免本步 diff 膨胀；改 AGENTS 时同步改 README）。
- `input.txt.example` 含 podcast URL 注释示例（纯注释，不影响运行；AGENTS 重写时一并清）。
- `logs/` 下可能残留历史 `temp/info_*.json`（spec §3：不管，由用户手删 GitHub 存量）。
- `.gitignore` 有一行 `.codegraph/` 修改，非本步骤产生（codegraph 索引工具写入），未动。
- `src/main.py` 仍有历史遗留未用导入（如 `sanitize_filename`、`get_file_size_mb` 等），
  本步未碰（ponytail：不重构不相关）。
