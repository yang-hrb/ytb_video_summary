"""Tests for issue 05: --max-hours in-process deadline, PENDING_KILLED, scan lock.

No real network: channel feeds are fake entries, the dedup DB is a temp file,
ProcessingPipeline is mocked (except the full-chain smoke test, which uses a
fake pipeline class + real generate_daily_summary + mocked GitHub upload).
"""

import os
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src import channel_watcher as cw
from src.channel_watcher import (
    ChannelWatcher,
    acquire_scan_lock,
    select_scan_videos,
)
from src.database import DatabaseManager
from src.run_tracker import init_videos_table, mark_video_completed


def _today():
    return datetime.now().strftime("%Y%m%d")


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.dedup = DatabaseManager(self.dir / "dedup.db")
        init_videos_table(self.dedup)

    def tearDown(self):
        self._tmp.cleanup()

    def _watcher(self, entries):
        with patch.object(cw, "get_tracker") as gt:
            from src.run_tracker import RunTracker
            gt.return_value = RunTracker(db_path=self.dir / "old.db")
            w = ChannelWatcher()
        w.fetch_channel_entries = lambda url, cutoff: entries
        return w

    def _channellist(self):
        ch = self.dir / "channellist.txt"
        ch.write_text("https://www.youtube.com/@ChanA\n", encoding="utf-8")
        return ch

    def _run_scan(self, w, ch, **kw):
        kw.setdefault("upload", False)
        with patch.object(cw, "get_dedup_db", return_value=self.dedup), \
             patch("src.batch._make_shared_transcriber", return_value=None), \
             patch("src.channel_watcher.ProcessingPipeline") as pipe, \
             patch("src.daily_summary.generate_daily_summary") as digest:
            n = w.execute_scan(channels_file=ch, **kw)
        return n, pipe, digest


class TestMaxHoursDeadline(_Base):
    def test_zero_budget_kills_everything_as_pending(self):
        # max_hours=0 → deadline already passed at first check (monotonic is
        # non-decreasing): nothing dispatched, all marked PENDING_KILLED.
        entries = [
            {"id": "v1", "upload_date": _today()},
            {"id": "v2", "upload_date": _today()},
        ]
        n, pipe, digest = self._run_scan(self._watcher(entries), self._channellist(),
                                         max_hours=0)
        self.assertEqual(n, 0)
        pipe.assert_not_called()
        for vid in ("v1", "v2"):
            row = self.dedup.execute_one("SELECT * FROM videos WHERE video_id = ?", (vid,))
            self.assertEqual(row["status"], "PENDING_KILLED")
            self.assertEqual(row["fail_count"], 0)  # timeout is "never ran"
        pending = digest.call_args.kwargs["run_results"]["pending"]
        self.assertEqual({r["video_id"] for r in pending}, {"v1", "v2"})

    def test_partial_timeout_processes_first_then_kills_rest(self):
        # newest-first [new2, new1] → dispatched oldest-first: new1 runs, new2 killed.
        entries = [
            {"id": "new2", "upload_date": _today()},
            {"id": "new1", "upload_date": _today()},
        ]
        calls = iter([1000.0, 1000.0, 99999.0])

        def fake_monotonic():
            return next(calls, 99999.0)

        w = self._watcher(entries)
        with patch("time.monotonic", side_effect=fake_monotonic):
            n, pipe, digest = self._run_scan(w, self._channellist(), max_hours=1)
        ran = [c.kwargs.get("url_or_path", "") for c in pipe.call_args_list]
        self.assertEqual(n, 1)
        self.assertEqual(ran, ["https://www.youtube.com/watch?v=new1"])
        row = self.dedup.execute_one("SELECT * FROM videos WHERE video_id = 'new2'")
        self.assertEqual(row["status"], "PENDING_KILLED")
        self.assertEqual(row["fail_count"], 0)
        pending = digest.call_args.kwargs["run_results"]["pending"]
        self.assertEqual([r["video_id"] for r in pending], ["new2"])

    def test_pending_killed_silently_reruns_next_scan(self):
        # PENDING_KILLED is neither COMPLETED (cursor) nor FAILED (skip) → re-selected.
        to_run, failed = select_scan_videos(
            [{"id": "k1", "upload_date": _today()}], {"k1": "PENDING_KILLED"}.get,
            (datetime.now() - timedelta(days=2)).strftime("%Y%m%d"))
        self.assertEqual([e["id"] for e in to_run], ["k1"])
        self.assertEqual(failed, [])

    def test_no_budget_behaves_as_before(self):
        entries = [{"id": "solo", "upload_date": _today()}]
        n, pipe, digest = self._run_scan(self._watcher(entries), self._channellist())
        self.assertEqual(n, 1)
        self.assertEqual(digest.call_args.kwargs["run_results"]["pending"], [])


class TestScanLock(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.lock = Path(self._tmp.name) / "scan.lock"

    def tearDown(self):
        self._tmp.cleanup()

    def test_second_acquire_returns_none(self):
        first = acquire_scan_lock(self.lock)
        self.assertIsNotNone(first)
        try:
            self.assertIsNone(acquire_scan_lock(self.lock))
        finally:
            first.unlink(missing_ok=True)
        self.assertIsNotNone(acquire_scan_lock(self.lock))
        self.lock.unlink(missing_ok=True)

    def test_stale_lock_is_reclaimed(self):
        self.lock.touch()
        old = datetime.now().timestamp() - 8 * 3600
        os.utime(self.lock, (old, old))
        got = acquire_scan_lock(self.lock)
        self.assertIsNotNone(got)
        got.unlink(missing_ok=True)


class TestMaxHoursHelp(unittest.TestCase):
    def test_max_hours_visible_in_help(self):
        from src.cli.parser import create_parser
        self.assertIn("--max-hours", create_parser().format_help())


class TestFullChainSmoke(_Base):
    """1 channel → new video → Digest → GitHub, all without network."""

    def test_scan_to_digest_to_github_upload(self):
        from config import config

        mark_video_completed(self.dedup, "done1", "http://x/done1")
        entries = [
            {"id": "fresh1", "upload_date": _today()},
            {"id": "done1", "upload_date": _today()},
        ]
        w = self._watcher(entries)

        dedup = self.dedup

        class FakePipeline:
            def __init__(self, **kw):
                pass

            def run_youtube(self, **kw):
                dedup.execute_update(
                    "INSERT OR IGNORE INTO videos (video_id, url, first_seen, status,"
                    " fail_count, updated_at) VALUES (?, ?, ?, 'COMPLETED', 0, ?)",
                    ("fresh1", "https://www.youtube.com/watch?v=fresh1",
                     "2026-09-06 04:00:00", "2026-09-06 04:01:00"),
                )
                dedup.execute_update(
                    "UPDATE videos SET md_path = ?, uploader = ?, title = ?,"
                    " duration_seconds = ?, updated_at = ? WHERE video_id = ?",
                    ("/tmp/fresh1.md", "ChanA", "Fresh Video", 60,
                     "2026-09-06 04:01:00", "fresh1"),
                )
                return {"reused": False}

        report_dir = self.dir / "summary"
        with patch.object(cw, "get_dedup_db", return_value=self.dedup), \
             patch("src.batch._make_shared_transcriber", return_value=None), \
             patch("src.channel_watcher.ProcessingPipeline", FakePipeline), \
             patch.object(config, "REPORT_DIR", report_dir), \
             patch.object(config, "GITHUB_TOKEN", "tok"), \
             patch.object(config, "GITHUB_REPO", "owner/repo"), \
             patch("src.github_handler.GitHubHandler") as gh:
            n = w.execute_scan(channels_file=self._channellist(), upload=True,
                               max_hours=4)
        self.assertEqual(n, 1)
        day = datetime.now().strftime("%Y-%m-%d")
        digest_file = report_dir / "daily_digest" / datetime.now().strftime("%Y_%m") / f"{day}.md"
        self.assertTrue(digest_file.exists())
        body = digest_file.read_text(encoding="utf-8")
        self.assertIn("Fresh Video", body)
        gh.return_value.upload_file.assert_called_once()


if __name__ == "__main__":
    unittest.main()
