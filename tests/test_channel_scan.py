"""Tests for issue 03: channel scan (2-day window, dedup-DB verdict, no N+1).

No real network: channel feeds are fake entries, the dedup DB is a temp file,
and ProcessingPipeline is mocked.
"""

import unittest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src import channel_watcher as cw
from src.channel_watcher import (
    ChannelWatcher,
    entry_publish_date,
    is_recent,
    read_channellist,
    select_scan_videos,
)
from src.database import DatabaseManager
from src.run_tracker import init_videos_table, mark_video_completed, mark_video_failed


def _today():
    return datetime.now().strftime("%Y%m%d")


def _days_ago(n):
    return (datetime.now() - timedelta(days=n)).strftime("%Y%m%d")


class TestReadChannellist(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_skips_blanks_and_comments(self):
        f = self.dir / "ch.txt"
        f.write_text(
            "\n"
            "# a comment\n"
            "   # indented comment\n"
            "https://www.youtube.com/@ChanA\n"
            "\n"
            "   https://www.youtube.com/channel/UC123   \n",
            encoding="utf-8",
        )
        self.assertEqual(
            read_channellist(f),
            ["https://www.youtube.com/@ChanA", "https://www.youtube.com/channel/UC123"],
        )

    def test_missing_file_creates_example_and_returns_empty(self):
        f = self.dir / "new_list.txt"
        self.assertEqual(read_channellist(f), [])
        self.assertTrue(f.exists())
        # Second read still parses (example file is all comments).
        self.assertEqual(read_channellist(f), [])


class TestEntryDate(unittest.TestCase):
    def test_upload_date_preferred(self):
        self.assertEqual(entry_publish_date({"upload_date": "20260905"}), "20260905")

    def test_timestamp_fallback(self):
        ts = datetime(2026, 9, 4, 12, 0, 0).timestamp()
        self.assertEqual(entry_publish_date({"timestamp": ts}), "20260904")

    def test_published_parsed_fallback(self):
        import time
        pp = time.strptime("2026-09-03", "%Y-%m-%d")
        self.assertEqual(entry_publish_date({"published_parsed": pp}), "20260903")

    def test_no_date_is_none(self):
        self.assertIsNone(entry_publish_date({"id": "x", "title": "t"}))

    def test_is_recent_requires_known_date(self):
        cutoff = _days_ago(2)
        self.assertTrue(is_recent({"upload_date": _today()}, cutoff))
        self.assertTrue(is_recent({"upload_date": cutoff}, cutoff))
        self.assertFalse(is_recent({"upload_date": _days_ago(3)}, cutoff))
        self.assertFalse(is_recent({}, cutoff))


class TestSelectScanVideos(unittest.TestCase):
    def test_completed_truncates_cursor(self):
        entries = [
            {"id": "new", "upload_date": _today()},
            {"id": "done", "upload_date": _today()},
            {"id": "older", "upload_date": _today()},
        ]
        to_run, failed = select_scan_videos(entries, {"done": "COMPLETED"}.get, _days_ago(2))
        self.assertEqual([e["id"] for e in to_run], ["new"])
        self.assertEqual(failed, [])

    def test_failed_listed_not_run(self):
        entries = [
            {"id": "bad", "upload_date": _today()},
            {"id": "good", "upload_date": _today()},
        ]
        to_run, failed = select_scan_videos(entries, {"bad": "FAILED"}.get, _days_ago(2))
        self.assertEqual([e["id"] for e in to_run], ["good"])
        self.assertEqual(failed, ["bad"])

    def test_old_entry_truncates(self):
        entries = [
            {"id": "fresh", "upload_date": _today()},
            {"id": "stale", "upload_date": _days_ago(10)},
            {"id": "after", "upload_date": _today()},
        ]
        to_run, failed = select_scan_videos(entries, {}.get, _days_ago(2))
        self.assertEqual([e["id"] for e in to_run], ["fresh"])
        self.assertEqual(failed, [])

    def test_undated_entry_counts_as_old(self):
        entries = [{"id": "nodate"}, {"id": "fresh", "upload_date": _today()}]
        to_run, _ = select_scan_videos(entries, {}.get, _days_ago(2))
        self.assertEqual(to_run, [])


class TestExecuteScan(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.dedup = DatabaseManager(self.dir / "dedup.db")
        init_videos_table(self.dedup)
        mark_video_completed(self.dedup, "done1", "http://x/done1")
        mark_video_failed(self.dedup, "bad1", "http://x/bad1", "boom")

    def tearDown(self):
        self._tmp.cleanup()

    def _watcher(self):
        with patch.object(cw, "get_tracker") as gt:
            from src.run_tracker import RunTracker
            gt.return_value = RunTracker(db_path=self.dir / "old.db")
            w = ChannelWatcher()
        w.fetch_channel_entries = lambda url, cutoff: [
            {"id": "fresh1", "upload_date": _today()},
            {"id": "bad1", "upload_date": _today()},
            {"id": "done1", "upload_date": _today()},
            {"id": "behind", "upload_date": _today()},
            {"id": "stale1", "upload_date": "20000101"},
        ]
        return w

    def test_scan_runs_only_new_recent_and_lists_failed(self):
        ch = self.dir / "channellist.txt"
        ch.write_text("https://www.youtube.com/@ChanA\n", encoding="utf-8")
        w = self._watcher()
        with patch.object(cw, "get_dedup_db", return_value=self.dedup), \
             patch("src.batch._make_shared_transcriber", return_value=None), \
             patch("src.channel_watcher.ProcessingPipeline") as pipe, \
             patch("src.daily_summary.generate_daily_summary") as digest:
            n = w.execute_scan(channels_file=ch, upload=False)
        ran = sorted(c.kwargs.get("url_or_path", "") for c in pipe.call_args_list)
        self.assertEqual(n, 1)
        self.assertEqual(ran, ["https://www.youtube.com/watch?v=fresh1"])
        digest.assert_called_once()

    def test_scan_flag_visible_in_help(self):
        from src.cli.parser import create_parser
        help_text = create_parser().format_help()
        self.assertIn("--scan", help_text)


if __name__ == "__main__":
    unittest.main()
