# Bug：flat 抓取无日期 → --scan 把新视频当旧视频跳过（2026-09-05 22:35）

## 现象

`--scan channellist.txt` 对 `https://www.youtube.com/@tech-shrimp/videos` 一个都不跑。
直接验证（`extract_flat: True`，playlistend=3）：

- 列表能抓到，最新 2 条为 `ky7_1K3wfAY`、`HhZcnM9tR7s`（标题正常）。
- 但每条的 `upload_date / timestamp / published_parsed / release_date` 全为 `None`。
  flat 条目实际只有 `id/title/duration/view_count/uploader_url/...`，没有日期键。

## 根因

`src/channel_watcher.py:entry_publish_date()` 三路取日期（upload_date → timestamp → published_parsed），
全缺时返回 `None`；`is_recent()` 把 `None` 判为旧；`select_scan_videos()` 遇到第一个旧/无日期条目直接 `break`。
于是：第一条就是无日期 → `to_process` 为空 → 整 channel 静默跳过。

连带：`fetch_channel_entries` 传的 `dateafter` 对 flat 列表页基本不起作用，日期过滤全靠抓到后的
`is_recent()` 客户端判断，无日期就全灭。不止这一个 channel，所有用 `/videos` flat 抓的 channel 都一样。

## 影响

- 凡走 `--scan` 的定时任务（每天 04:00）都会漏跑：列表可见、Digest 里无影，且无任何失败记录（不算 FAILED，不进红区）。
- `-video <url>` 单跑不受影响（不走日期判定）。

## 复现

```bash
/Users/yangyu/github/ytb_video_summary/venv/bin/python -c "
from src.youtube_handler import build_ydl_opts, _run_ydl_with_cookie_fallback
opts = build_ydl_opts(cookies_file=None, cookies_from_browser=False, browser='chrome', overrides={'extract_flat': True, 'playlistend': 3})
res = _run_ydl_with_cookie_fallback(cookies_file=None, cookies_from_browser=False, browser='chrome', ydl_opts=opts, context='test', action=lambda ydl: ydl.extract_info('https://www.youtube.com/@tech-shrimp/videos', download=False))
e = list(res.get('entries', []))[0]
print({k: e.get(k) for k in ['id','title','upload_date','timestamp','published_parsed']})
"
# → {'id': 'ky7_1K3wfAY', ..., 'upload_date': None, 'timestamp': None, 'published_parsed': None}
```

## 修复方向（待定其一）

1. 无日期不再当旧：`is_recent()` 对 `None` 返回 True（或单独标记 unknown），照跑不照拦；代价是 2 天窗口失效，退化为 COMPLETED 游标去重。
2. 逐视频补日期：对无日期条目前 N 个调 `extract_info(watch?v=...)` 取 `upload_date` 再判；准但慢（每个多一次请求）。
3. 换 feed：用 RSS（`https://www.youtube.com/feeds/videos.xml?channel_id=...`）拿 `published`，flat 列表只做 ID 发现。

建议：先按方向 1 保命（有跑总比全跳过强），方向 2/3 后续再做。修完后用该 channel 做验收：`--scan` 应至少列出上述 2 个视频。
