# 06-summary：summarizer 保命截断 + waterfall 错误汇总 + 400 细分

## 做了什么

按 `issues/06-summarizer-harden.md` checklist 与 spec §8（只做保命截断 + waterfall
错误汇总 + 400 细分，禁 map-reduce），给 `Summarizer` 加三处硬化。未提交 git。

## 改了什么代码

- `src/summarizer.py`：
  - `MAX_TRANSCRIPT_CHARS = 60000`（类常量，约 15000 tokens，给 prompt 模板 +
    `max_tokens` 留余量）。
  - `_truncate_transcript()`（新增 classmethod，5 行）：超限则 `logger.warning`
    打出截断前后字符数并返回 `text[:N]`；未超限原样返回。
  - `create_prompt()`：`clean_srt_content` 后过一遍截断（覆盖 `summarize` 默认分支）。
  - `summarize()`：`custom_prompt` 分支同样截断（两条 prompt 入口全覆盖，无分块逻辑）。
  - `_is_auth_error()`（新增，1 行）：仅 `401/403` 判鉴权。
  - `_summarize_with_waterfall()`：`failures` 列表收集 `"{model} (attempt n/3,
    status=s): err"`；`401/403` 直接 `raise RuntimeError(auth failed...)` 停瀑布；
    其余（含 400 模型不存在/无效、404/422、耗尽重试的 429/5xx、解析错误）记失败 +
    warning 切下一个模型；最终抛 `RuntimeError("All OpenRouter models failed:
    <model: 原因; ...>")`（前缀兼容旧消息，无新异常类）。
- `tests/test_summarizer_harden.py`（新增，6 tests，全部 mock `requests.post`，零真实 API）：
  截断进 prompt + warning 日志 / 短文本无日志 / custom_prompt 分支截断 /
  400 切下一模型成功 / 401 直接停（第二模型零调用）/ 全灭消息含模型名与状态码。

## 截断阈值

`MAX_TRANSCRIPT_CHARS = 60000`，截前 N 字符（保命掐尾，不做 map-reduce 分块；
尾部内容丢失是有意取舍，warning 日志可查）。

## waterfall 语义

- `429/5xx`：单模型内最多 3 次（`2s/4s` backoff）后切下一模型。
- `400/404/422` 等非鉴权错误：不重试，直接切下一模型。
- `401/403`：立即停，抛 `RuntimeError("OpenRouter auth failed (401/403)...")`。
- 全灭：`RuntimeError("All OpenRouter models failed: m1: 原因; m2: 原因...")`；
  无 key/无模型时 detail 为 `no models configured or no API key`。

## 测试命令 + 结果

- `python -m unittest tests.test_summarizer_harden` → Ran 6 tests, OK
- `python -m unittest discover tests` → **Ran 84 tests, OK**（78 原有 + 6 新增）
- 无真跑验证（需 OPENROUTER key；mock 已覆盖三条语义）

## 风险 / 下一步

- 截断丢尾：超长视频后半段进不了摘要；spec 已明确不要分块，可接受。
- 旧行为变更：以前非重试错误（400 等）是裸 `raise` 中断整个瀑布，现在改为换
  下一模型——这是 issue 本意；若某 400 是 prompt 本身问题（如超限），会把 4 个
  模型各试一遍才报错，浪费几次调用（截断后概率低）。
- `401/403` 现在抛 `RuntimeError` 而非原 `HTTPError`，调用方若按异常类型区分
  会受影响；已 grep 确认无按类型捕获（pipeline 侧走通用失败记账）。
