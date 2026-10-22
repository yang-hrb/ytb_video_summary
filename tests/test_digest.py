"""Tests for issue 04: cross-day digest + four sections + two_time_fail.

Temp DB + fake rows only. No real API calls, no real logs/ or output/ writes
(config.LOG_DIR / REPORT_DIR are patched to tmpdirs).
"""

import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from config import config
from src.daily_summary import generate_daily_summary
from src.database import DatabaseManager
from src.run_tracker import (
    TWO_TIME_FAIL_NAME,
    init_videos_table,
    mark_video_completed,
    mark_video_failed,
    mark_video_pending_killed,
)


def _make_db(tmpdir: str) -> DatabaseManager:
    db = DatabaseManager(Path(tmpdir) / "dedup.db")
    init_videos_table(db)
    return db


def _patch_dirs(testcase, tmpdir: str):
    testcase._log_patch = patch.object(config, 'LOG_DIR', Path(tmpdir) / "logs")
    testcase._rep_patch = patch.object(config, 'REPORT_DIR', Path(tmpdir) / "summary")
    testcase._log_patch.start()
    testcase._rep_patch.start()
    testcase.addCleanup(testcase._log_patch.stop)
    testcase.addCleanup(testcase._rep_patch.stop)


class TestTwoTimeFail(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.db = _make_db(self._tmp.name)
        _patch_dirs(self, self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_second_failure_appends_csv_line(self):
        n1 = mark_video_failed(self.db, 'vid2', 'http://x/vid2', 'boom1')
        self.assertEqual(n1, 1)
        self.assertFalse((Path(self._tmp.name) / "logs" / TWO_TIME_FAIL_NAME).exists())
        n2 = mark_video_failed(self.db, 'vid2', 'http://x/vid2', 'boom2')
        self.assertEqual(n2, 2)
        path = Path(self._tmp.name) / "logs" / TWO_TIME_FAIL_NAME
        with open(path, encoding='utf-8') as f:
            rows = list(csv.reader(f))
        self.assertEqual(len(rows), 1)
        # video_id,url,第一次,第二次,错误
        self.assertEqual(rows[0][0], 'vid2')
        self.assertEqual(rows[0][1], 'http://x/vid2')
        self.assertEqual(rows[0][4], 'boom2')
        self.assertTrue(rows[0][2])  # first failure time
        self.assertTrue(rows[0][3])  # second failure time

    def test_pending_killed_does_not_bump_fail_count(self):
        mark_video_failed(self.db, 'vid9', 'http://x/vid9', 'once')
        mark_video_pending_killed(self.db, 'vid9', 'http://x/vid9')
        row = self.db.execute_one("SELECT status, fail_count FROM videos WHERE video_id = ?",
                                  ('vid9',))
        self.assertEqual(row['status'], 'PENDING_KILLED')
        self.assertEqual(row['fail_count'], 1)

    def test_pending_killed_never_clobbers_completed(self):
        mark_video_completed(self.db, 'done1', 'http://x/done1', md_path='/tmp/d.md')
        mark_video_pending_killed(self.db, 'done1', 'http://x/done1')
        row = self.db.execute_one("SELECT status FROM videos WHERE video_id = ?",
                                  ('done1',))
        self.assertEqual(row['status'], 'COMPLETED')


class TestDigest(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.db = _make_db(self._tmp.name)
        _patch_dirs(self, self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _seed(self):
        mark_video_completed(self.db, 'new1', 'http://x/new1', md_path='/tmp/n1.md',
                             uploader='SomeChannel', title='New Video', duration_seconds=3661)
        mark_video_completed(self.db, 'reuse1', 'http://x/reuse1', md_path='/tmp/r1.md',
                             uploader='OldChannel', title='Old Video', duration_seconds=60)
        mark_video_failed(self.db, 'bad1', 'http://x/bad1', 'err1')
        mark_video_failed(self.db, 'bad1', 'http://x/bad1', 'err2')
        mark_video_pending_killed(self.db, 'todo1', 'http://x/todo1')

    def _read(self, out):
        with open(out, encoding='utf-8') as f:
            return f.read()

    def test_four_sections_and_db_columns(self):
        self._seed()
        new = self.db.execute("SELECT * FROM videos WHERE video_id = 'new1'")
        reused = self.db.execute("SELECT * FROM videos WHERE video_id = 'reuse1'")
        out = generate_daily_summary(target_date='20260905', upload=False,
                                     run_results={'new': new, 'reused': reused}, db=self.db)
        self.assertTrue(out.endswith('2026-09-05.md'))
        body = self._read(out)
        for section in ('## 🔴 Failures', '## New Reports', '## Reused References',
                        '## Unprocessed'):
            self.assertIn(section, body)
        # red zone: twice-failed with reason
        self.assertIn('bad1', body)
        self.assertIn('err2', body)
        # columns used directly, durations summed (3661 = 1h 1m 1s)
        self.assertIn('SomeChannel', body)
        self.assertIn('New Video', body)
        self.assertIn('OldChannel', body)
        self.assertIn('1h 1m 1s', body)
        # pending listed
        self.assertIn('todo1', body)

    def test_cross_day_single_file_uses_start_date(self):
        # Run spilling past midnight still lands in the start-day file.
        self._seed()
        new = self.db.execute("SELECT * FROM videos WHERE video_id = 'new1'")
        out = generate_daily_summary(target_date='20260905', upload=False,
                                     run_results={'new': new, 'reused': []}, db=self.db)
        self.assertIn('2026-09-05.md', out)
        self.assertNotIn('2026-09-06', out)
        body = self._read(out)
        self.assertIn('# Daily Summary for 2026-09-05', body)

    def test_standalone_mode_queries_db_by_date(self):
        self._seed()
        today = __import__('datetime').datetime.now().strftime('%Y%m%d')
        out = generate_daily_summary(target_date=today, upload=False, db=self.db)
        body = self._read(out)
        # standalone: COMPLETED rows dated today show as new; reused section empty
        self.assertIn('New Video', body)
        self.assertIn('bad1', body)  # red zone from DB regardless of date
        self.assertIn('todo1', body)  # pending from DB

    def test_all_empty_returns_none(self):
        out = generate_daily_summary(target_date='20200101', upload=False, db=self.db)
        self.assertIsNone(out)


if __name__ == '__main__':
    unittest.main()
