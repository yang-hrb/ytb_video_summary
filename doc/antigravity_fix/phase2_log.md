# Phase 2 实施日志

> **实施日期**: 2026-03-19  
> **基于**: `doc/antigravity_action_plan_20250319.md` Phase 2（第 114–325 行）  
> **参考**: Phase 1 已在 `doc/phase1_log.md` 完成  
> **测试结果**: 19 个单元测试全部通过 ✅

---

## 总结

Phase 2 在 Phase 1（代码清理）的基础上，完成了核心 Pipeline 重构、精确阶段追踪、断点续传升级、mlx-whisper Apple Silicon 优化，以及 Pipeline/Batch 模块抽象。

---

## 2.1 新状态机设计

状态流转现已覆盖完整生命周期：

```
PENDING → DOWNLOADING → TRANSCRIBING → TRANSCRIPT_READY → SUMMARIZING → SUMMARY_READY → UPLOADING → COMPLETED
                ↓               ↓                               ↓                              ↓
         DOWNLOAD_FAILED  TRANSCRIBE_FAILED              SUMMARIZE_FAILED              UPLOAD_FAILED
```

---

## 2.2 升级 RunTracker（`src/run_tracker.py`）

### DB Schema 新增字段（向后兼容 ALTER TABLE 迁移）

在 `_init_database()` 中通过 `PRAGMA table_info` 检测后按需执行 `ALTER TABLE`：

| 新列 | 类型 | 用途 |
|------|------|------|
| `transcript_path` | TEXT | SRT 文件路径 |
| `summary_path` | TEXT | Markdown 摘要路径 |
| `report_path` | TEXT | 报告文件路径 |
| `github_url` | TEXT | GitHub 上传 URL |
| `model_used` | TEXT | 使用的 AI 模型名称 |
| `audio_path` | TEXT | 音频文件路径（用于断点续传） |
| `summary_style` | TEXT | 摘要风格 (brief/detailed) |
| `retry_count` | INTEGER | 重试计数（默认 0） |

### 新增方法

| 方法 | 功能 |
|------|------|
| `update_artifacts(run_id, **kwargs)` | 批量更新产物路径（过滤未知字段，无副作用） |
| `increment_retry(run_id)` | 原子递增 retry_count |
| `RESUMABLE_STATUS_MAP` (类变量) | 完整的可恢复状态→恢复阶段映射表 |

### 升级 `get_resumable_runs()` 和 `get_failed_runs()`

- `get_resumable_runs()` 默认覆盖所有 8 种可恢复状态（含旧版别名如 `TRANSCRIPT_GENERATED`、`SUMMARY_FAILED`）
- `get_failed_runs()` 覆盖所有失败状态（`DOWNLOAD_FAILED`、`TRANSCRIBE_FAILED`、`SUMMARIZE_FAILED`、`SUMMARY_FAILED` 旧版、`UPLOAD_FAILED`、`failed` 旧版）

---

## 2.3 Pipeline 抽象（Phase 2.7）— `src/pipeline.py`（新建）

新建 `ProcessingPipeline` 类，封装完整的下载→转录→摘要→上传逻辑：

```python
STAGE_TO_FAILED_STATUS = {
    'download':   'DOWNLOAD_FAILED',
    'transcribe': 'TRANSCRIBE_FAILED',
    'summarize':  'SUMMARIZE_FAILED',
    'upload':     'UPLOAD_FAILED',
}
```

**核心设计**：
- `current_stage` 变量在每个关键步骤前更新
- 统一的 `_fail(error)` 方法根据 `current_stage` 动态写入正确的失败状态
- `_complete()` 方法在成功时调用 `update_artifacts()` 记录所有产物路径
- 提供三个 `run_*()` 方法：`run_youtube()`、`run_local_mp3()`、`run_podcast()`
- 支持注入共享 `Transcriber` 实例（批量处理时避免重复加载模型）

---

## 2.4 升级断点续传（`src/pipeline.py` → `ProcessingPipeline.resume()`）

静态方法 `ProcessingPipeline.resume(run, ...)` 实现智能阶段恢复：

| 失败状态 | 恢复策略 |
|----------|----------|
| `DOWNLOAD_FAILED` | 通知调用方需完全重新处理 |
| `TRANSCRIBE_FAILED` | 检查音频文件是否存在 → 存在则重新转录，否则降级为 DOWNLOAD_FAILED |
| `TRANSCRIPT_READY` / `SUMMARIZE_FAILED` / `SUMMARY_FAILED` | 从已有 SRT 重新摘要 |
| `SUMMARY_READY` / `UPLOAD_FAILED` | 直接重新上传已有报告 |

每次 resume 调用 `increment_retry()` 记录重试次数。

---

## 2.5 新增 CLI 诊断命令（`src/main.py`）

```bash
# 显示处理统计（按状态和类型分组）
python src/main.py --status

# 列出所有失败 run 的阶段和错误信息
python src/main.py --list-failed

# 列出所有可恢复的 run 及恢复阶段
python src/main.py --list-resumable
```

**验证输出**：

```
📊 Processing Statistics
========================================
  Total runs: 34

By status:
  COMPLETED                 4
  SUMMARY_FAILED            1
  ...

🔄 Resumable runs (1)
============================================================
  id=30 | status=SUMMARY_FAILED → resume from: summarize
    identifier : ezT2jmo0tPM

❌ Failed runs (6)
============================================================
  id=30 | status=SUMMARY_FAILED | stage=summarize
    identifier : ezT2jmo0tPM
    error      : 404 Client Error: Not Found
```

---

## 2.6 切换 mlx-whisper（Apple Silicon 优化）

### `config/settings.py`

新增 `WHISPER_BACKEND` 配置项（默认 `'auto'`）和静态方法 `resolve_whisper_backend()`：

```python
@staticmethod
def resolve_whisper_backend() -> str:
    backend = Config.WHISPER_BACKEND.lower().strip()
    if backend == 'auto':
        if platform.system() == 'Darwin' and platform.machine() == 'arm64':
            return 'mlx'
        return 'openai'
    return backend if backend in ('mlx', 'openai') else 'openai'
```

**验证**：当前机器 Darwin arm64 → 自动选择 `mlx` ✅

### `src/transcriber.py`（重构为适配器模式）

| 组件 | 职责 |
|------|------|
| `_OpenAIWhisperBackend` | 封装 `import whisper` + `model.transcribe()` |
| `_MLXWhisperBackend` | 封装 `import mlx_whisper` + HF repo 模型名映射；mlx_whisper 缺失时优雅降级 |
| `_create_backend(model_name)` | 工厂方法，根据 `config.resolve_whisper_backend()` 选择后端 |
| `Transcriber`（公开 API 不变） | 委托给后端适配器 |

**模型名映射（`_MLXWhisperBackend.MODEL_MAP`）**：

| 官方名 | mlx-community repo |
|--------|-------------------|
| tiny | mlx-community/whisper-tiny-mlx |
| base | mlx-community/whisper-base-mlx |
| small | mlx-community/whisper-small-mlx |
| medium | mlx-community/whisper-medium-mlx |
| large | mlx-community/whisper-large-v3-mlx |
| turbo | mlx-community/whisper-turbo |

### `requirements.txt`（更新）

```txt
mlx-whisper>=0.4.0; sys_platform == 'darwin' and platform_machine == 'arm64'
openai-whisper>=20231117; sys_platform != 'darwin' or platform_machine != 'arm64'
```

### `.env.example`（更新）

新增 `WHISPER_BACKEND=auto` 配置项及注释说明。

---

## 2.7 Batch 模块抽象（`src/batch.py` 新建，`src/main.py` 重构）

将批量处理逻辑从 `main.py` 提取为独立模块：

| 函数 | 职责 |
|------|------|
| `process_playlist_batch()` | YouTube 播放列表处理 |
| `process_local_folder_batch()` | 本地 MP3 文件夹处理 |
| `process_podcast_show_batch()` | Apple Podcasts 节目全集处理 |
| `process_batch_file()` | 混合批量文件处理（自动识别类型） |

**共享 Transcriber 优化**：批量函数调用 `_make_shared_transcriber()` 预加载一次 Whisper 模型，批量处理时避免重复加载。

### `src/main.py` 重构

所有 `process_*()` 函数现委托给 `pipeline.py` / `batch.py`：

- `process_video()` → `ProcessingPipeline.run_youtube()`
- `process_local_mp3()` → `ProcessingPipeline.run_local_mp3()`
- `process_apple_podcast()` → `ProcessingPipeline.run_podcast()`
- `process_local_folder()` → `batch.process_local_folder_batch()`
- `process_playlist()` → `batch.process_playlist_batch()`
- `process_apple_podcast_show()` → `batch.process_podcast_show_batch()`
- `process_resume_only()` → `ProcessingPipeline.resume()`（新增 `upload` 参数传递）

---

## 新增/修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/run_tracker.py` | ✏️ 修改 | 8 列迁移 + 3 个新方法 + RESUMABLE_STATUS_MAP |
| `src/transcriber.py` | ✏️ 重构 | 双后端适配器（openai / mlx） |
| `config/settings.py` | ✏️ 修改 | WHISPER_BACKEND + resolve_whisper_backend() |
| `.env.example` | ✏️ 修改 | 新增 WHISPER_BACKEND 文档 |
| `requirements.txt` | ✏️ 修改 | 平台条件 mlx-whisper / openai-whisper |
| `src/pipeline.py` | 🆕 新建 | ProcessingPipeline（阶段追踪 + 断点续传） |
| `src/batch.py` | 🆕 新建 | 批量处理模块（共享 Transcriber） |
| `src/main.py` | ✏️ 修改 | 委托 + 三个新 CLI 诊断命令 |
| `tests/test_run_tracker.py` | 🆕 新建 | 11 个 RunTracker Phase-2 单元测试 |

---

## Phase 2 验证结果

```bash
# 1. DB 迁移测试
python -c "from src.run_tracker import RunTracker; t = RunTracker(); print('OK')"
# 输出: OK ✅

# 2. RunTracker 单元测试（11/11 通过）
python -m unittest tests/test_run_tracker.py -v
# Ran 11 tests in 0.131s — OK ✅

# 3. 全套测试（19/19 通过）
python -m unittest discover tests
# Ran 19 tests in 0.087s — OK ✅

# 4. mlx-whisper 后端自动检测
# Darwin arm64 → mlx ✅；WHISPER_BACKEND=openai → openai ✅

# 5. 诊断命令
python src/main.py --status          # ✅
python src/main.py --list-resumable  # ✅
python src/main.py --list-failed     # ✅
```

---

## 遗留说明

- **`process_batch_file()` 别名**：`main.py` 以 `_process_batch_file` 导入 `batch.py` 中的同名函数，避免命名冲突。
- **旧状态名兼容**：`TRANSCRIPT_GENERATED`（旧）= `TRANSCRIPT_READY`（新），`SUMMARY_FAILED`（旧）= `SUMMARIZE_FAILED`（新），两者均已纳入 `RESUMABLE_STATUS_MAP`，现有数据库记录无需迁移。
- **mlx-whisper 安装**：需在 Apple Silicon 机器上重新运行 `pip install -r requirements.txt` 安装 `mlx-whisper`。
