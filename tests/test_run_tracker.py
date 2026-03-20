"""Tests for Phase-2 RunTracker upgrades.

Covers:
  - DB migration: 8 new columns added to existing schema
  - update_artifacts()
  - increment_retry()
  - get_resumable_runs() with full Phase-2 status vocabulary
  - get_failed_runs() with full Phase-2 status vocabulary
  - RESUMABLE_STATUS_MAP completeness
"""

import tempfile
import unittest
from pathlib import Path

from src.run_tracker import RunTracker


class TestRunTrackerPhase2(unittest.TestCase):

    def setUp(self):
        # Use an in-memory-like temp file so tests are isolated
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.db_path = Path(self._tmp.name)
        self.tracker = RunTracker(db_path=self.db_path)

    def tearDown(self):
        self.db_path.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Schema / migration
    # ------------------------------------------------------------------

    def test_phase2_columns_exist(self):
        """All 8 Phase-2 columns must be present after init."""
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(runs)")
            columns = {row[1] for row in cursor.fetchall()}
        expected = {
            "transcript_path", "summary_path", "report_path",
            "github_url", "model_used", "audio_path",
            "summary_style", "retry_count",
        }
        self.assertTrue(expected.issubset(columns),
                        f"Missing columns: {expected - columns}")

    def test_migration_idempotent(self):
        """Running _init_database() again must not raise."""
        self.tracker._init_database()  # second call

    # ------------------------------------------------------------------
    # update_artifacts
    # ------------------------------------------------------------------

    def test_update_artifacts_basic(self):
        run_id = self.tracker.start_run("youtube", "http://example.com", "vid123")
        self.tracker.update_artifacts(
            run_id,
            transcript_path="/tmp/vid123.srt",
            summary_path="/tmp/vid123_summary.md",
            report_path="/tmp/vid123_report.md",
            github_url="https://github.com/repo/blob/main/vid123_report.md",
            model_used="deepseek-r1",
            summary_style="detailed",
        )
        info = self.tracker.get_run_info(run_id)
        self.assertEqual(info["transcript_path"], "/tmp/vid123.srt")
        self.assertEqual(info["github_url"],
                         "https://github.com/repo/blob/main/vid123_report.md")
        self.assertEqual(info["model_used"], "deepseek-r1")
        self.assertEqual(info["summary_style"], "detailed")

    def test_update_artifacts_ignores_unknown_keys(self):
        """Unknown kwargs must be silently ignored (no crash)."""
        run_id = self.tracker.start_run("local", "/path/to/file.mp3", "file")
        self.tracker.update_artifacts(run_id, nonexistent_column="value")
        info = self.tracker.get_run_info(run_id)
        self.assertIsNotNone(info)  # row still exists and is valid

    def test_update_artifacts_noop_when_empty(self):
        run_id = self.tracker.start_run("local", "/path/to/file.mp3", "noop")
        self.tracker.update_artifacts(run_id)  # nothing passed — should not raise

    # ------------------------------------------------------------------
    # increment_retry
    # ------------------------------------------------------------------

    def test_increment_retry(self):
        run_id = self.tracker.start_run("youtube", "http://example.com", "retrytest")
        self.tracker.increment_retry(run_id)
        info = self.tracker.get_run_info(run_id)
        self.assertEqual(info["retry_count"], 1)

        self.tracker.increment_retry(run_id)
        self.tracker.increment_retry(run_id)
        info = self.tracker.get_run_info(run_id)
        self.assertEqual(info["retry_count"], 3)

    # ------------------------------------------------------------------
    # RESUMABLE_STATUS_MAP
    # ------------------------------------------------------------------

    def test_resumable_status_map_completeness(self):
        """RESUMABLE_STATUS_MAP must cover all expected statuses."""
        expected_keys = {
            "DOWNLOAD_FAILED", "TRANSCRIBE_FAILED",
            "TRANSCRIPT_READY", "TRANSCRIPT_GENERATED",
            "SUMMARIZE_FAILED", "SUMMARY_FAILED",
            "SUMMARY_READY", "UPLOAD_FAILED",
        }
        self.assertEqual(
            expected_keys,
            set(RunTracker.RESUMABLE_STATUS_MAP.keys()),
            f"Map mismatch: {expected_keys.symmetric_difference(RunTracker.RESUMABLE_STATUS_MAP)}",
        )

    # ------------------------------------------------------------------
    # get_resumable_runs
    # ------------------------------------------------------------------

    def test_get_resumable_runs_returns_all_resumable_statuses(self):
        for status in RunTracker.RESUMABLE_STATUS_MAP:
            run_id = self.tracker.start_run("youtube", f"http://x.com/{status}", status)
            self.tracker.update_status(run_id, status, stage="test")

        runs = self.tracker.get_resumable_runs()
        returned_statuses = {r["status"] for r in runs}
        for expected in RunTracker.RESUMABLE_STATUS_MAP:
            self.assertIn(expected, returned_statuses,
                          f"Status {expected!r} not returned by get_resumable_runs()")

    def test_get_resumable_runs_excludes_completed(self):
        run_id = self.tracker.start_run("youtube", "http://done.com", "done")
        self.tracker.update_status(run_id, "COMPLETED", stage="done")
        runs = self.tracker.get_resumable_runs()
        statuses = {r["status"] for r in runs}
        self.assertNotIn("COMPLETED", statuses)

    # ------------------------------------------------------------------
    # get_failed_runs
    # ------------------------------------------------------------------

    def test_get_failed_runs_covers_all_failed_statuses(self):
        failed_statuses = [
            "DOWNLOAD_FAILED", "TRANSCRIBE_FAILED",
            "SUMMARIZE_FAILED", "SUMMARY_FAILED",
            "UPLOAD_FAILED", "failed",
        ]
        for status in failed_statuses:
            run_id = self.tracker.start_run("youtube", f"http://fail.com/{status}", status)
            self.tracker.update_status(run_id, status, stage="test")

        runs = self.tracker.get_failed_runs()
        returned = {r["status"] for r in runs}
        for expected in failed_statuses:
            self.assertIn(expected, returned,
                          f"Status {expected!r} missing from get_failed_runs()")

    def test_get_failed_runs_limit(self):
        for i in range(5):
            run_id = self.tracker.start_run("local", f"/tmp/f{i}.mp3", f"f{i}")
            self.tracker.update_status(run_id, "DOWNLOAD_FAILED")
        runs = self.tracker.get_failed_runs(limit=2)
        self.assertEqual(len(runs), 2)


if __name__ == "__main__":
    unittest.main()
