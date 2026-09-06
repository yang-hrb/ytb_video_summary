# Ponytail 全仓审计 — over-engineering（2026-09-05 22:01）

范围：整仓（`src/` 约 4200 行 + `scripts/` + `config/`），只看过度工程，不看正确性/安全/性能。上一轮 01–07 之后仍有大块旧系统残留：新去重库 `videos` 已是唯一口径，但旧 `runs` 状态机、watch 表、resume、diagnostics、batch 混装全还留着。

## 发现（省行数从大到小，一行一条）

delete 旧 runs 状态机整套（runs/file_storage/watch_channels/watch_channel_state/watch_scan_runs/web_jobs/web_job_runs 建表 + start_run/update_status/update_artifacts/increment_retry/get_run_info/find_latest_completed_report）。只留 videos 表，迁移后 runs 只读一次。 [src/run_tracker.py:292-646]
delete `ProcessingPipeline.resume()` 120 行 smart resume（DOWNLOAD/TRANSCRIBE/SUMMARIZE/UPLOAD 四分支 + 重传重摘要）。videos 表无断点续跑语义，直接重跑即可。 [src/pipeline.py:353-477]
delete `--batch` 混装入口 + `process_batch_file`（三层嵌套、playlist 内再起共享 Transcriber）。spec 只留四命令，batch 不在其中。 [src/batch.py:157-243, src/main.py:116-135, src/cli/parser.py:62-67]
delete watcher 旧模式（`--import-watchlist/--list-watch-channels/--watch-run-once/--watch-daemon/--watch-time` + import_watchlist/list_watch_channels + legacy_state 回写）。channellist.txt 已替代。 [src/cli/parser.py:165-175, src/cli/commands.py:108-154, src/channel_watcher.py:159-191]
delete diagnostics 四件套（`--status/--list-failed/--list-resumable/--resume-only` + display_stats/failed/resumable）。读的是旧 runs 表，AGENTS 已声明不宣传。 [src/cli/parser.py:76-92, src/cli/commands.py:85-106, src/cli/display.py:29-73]
delete 旧脚本堆（full_auto_run_playlist/mp3/input_txt/batch-run/watch-run/quick-run）。daily_scan.sh 已是唯一入口。 [scripts/full_auto_run_playlist.sh, scripts/full_auto_run_mp3.sh, scripts/full_auto_run_input_txt.sh, scripts/batch-run.sh, scripts/watch-run.sh, scripts/quick-run.sh]
delete `scripts/diagnostics/` 三个一次性诊断脚本。`python -c` + yt-dlp --version 即可。 [scripts/diagnostics/diag_api_key.py, scripts/diagnostics/diag_ffmpeg.py, scripts/diagnostics/diag_whisper_ffmpeg.py]
delete `failures_*.txt` 会话失败日志（log_failure + cleanup_old_logs）。two_time_fail.txt + Digest 红区已覆盖失败去向。 [src/run_tracker.py:649-715, src/pipeline.py:115]
delete `upload_logs_to_github` + `get_current_log_file` 日志上传链。spec 只要 Digest 上 GitHub。 [src/github_handler.py:172, src/logger.py:114, src/cli/commands.py:316-319]
delete `transcribe_video_audio` + `detect_language_from_text` 薄包装。调用方都用 Transcriber 方法。 [src/transcriber.py:199-238]
delete `tests/test_file_storage.py` + `tests/test_run_tracker.py` 旧 runs API 测试。随旧表一起删。 [tests/test_file_storage.py, tests/test_run_tracker.py]
yagni `GitHubHandler` 类（单调用方 upload_file）。只留 `upload_to_github()` 函数。 [src/github_handler.py:13-120]
yagni `main.py` 四个薄转发（process_video/process_playlist/process_local_folder/process_local_mp3）。CLI 直接调 pipeline/batch 即可。 [src/main.py:39-113]
yagni `--force` + `--no-reuse` 双 flag 同一 bool（_force 属性合并）。留一个。 [src/cli/parser.py:144-163, src/cli/commands.py:30-32]
yagni `_make_shared_transcriber()` 一行包装（三调用方）。内联 `Transcriber(); load_model()`。 [src/batch.py:19-23, src/channel_watcher.py:253]
yagni `STAGE_TO_FAILED_STATUS` 映射（_fail 内 `del status` 根本不用）。删表，_fail 只记字符串。 [src/pipeline.py:30-36, src/pipeline.py:107-115, src/main.py:32]
yagni `PipelineError` 九子类单层继承（仅透传 message/stage）。留 PipelineError + DatabaseError 即可。 [src/exceptions.py:11-90]
yagni `console_print` + banner/statistics 七个 display 函数。print 足够，banner 纯装饰。 [src/cli/display.py:12-86]
native `colorama` 依赖（logger + display + main 三处 init/Fore/Style）。终端原生 ANSI 即可。 [src/logger.py:10, src/cli/display.py:6, src/main.py:17, requirements.txt]
stdlib `_VIDEOS_EXTRA_COLUMNS` 重复加列（DDL 已含 uploader/title/duration_seconds）。删该名单。 [src/run_tracker.py:55-60]
shrink `mark_video_completed/failed/pending_killed` 皆 INSERT OR IGNORE + UPDATE 两语句。合为单条 ON CONFLICT DO UPDATE。 [src/run_tracker.py:119-198]
shrink `migrate_legacy_db` 45 行四分支（rename/import/both/empty）。只留“backup 存在且 videos 为空才导”一路。 [src/run_tracker.py:201-246]
shrink `local_content_id` while 读 1MB 循环。`iter(lambda: f.read(1<<20), b'')` 两行。 [src/run_tracker.py:83-96]
shrink `batch.py` 三个批循环各自 log/failed/_log_summary。抽一个 `_run_each()`。 [src/batch.py:30-150]
shrink `_set_stage(stage, status)` 恒 `del status`。去第二个参数。 [src/pipeline.py:77-79]
shrink `_complete()` 五个 `del` 占位参数。只留 report/github/uploader/title/duration。 [src/pipeline.py:117-131]
shrink `read_channellist` 手写 strip/注释跳过。列表推导一行。 [src/channel_watcher.py:26-41]
shrink `entry_publish_date` 三段 try（upload_date/timestamp/published_parsed）。单辅助 `_coerce_yyyymmdd()`。 [src/channel_watcher.py:88-109]
shrink `select_scan_videos` 三重 break 游标。先定截断点再切片。 [src/channel_watcher.py:118-147]
shrink `generate_daily_summary` content 列表 40 行拼接。模板字符串一次 join。 [src/daily_summary.py:81-124]
shrink `utils.format_duration/format_timestamp/create_summary_header` 三个小排版。调用处 f-string 即可。 [src/utils.py:176-328]

net: -~1400 行, -1 依赖（colorama）可删。
