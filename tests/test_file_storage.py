import unittest
import os
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

from src.run_tracker import RunTracker

class TestFileStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_run_track.db"
        self.tracker = RunTracker(db_path=self.db_path)
        
    def tearDown(self):
        self.temp_dir.cleanup()
        
    def test_register_and_get_files(self):
        run_id = self.tracker.start_run('youtube', 'url', 'test_vid')
        
        fid1 = self.tracker.register_file(run_id, 'transcript', '/path/to/trans.srt', 100)
        fid2 = self.tracker.register_file(run_id, 'summary', '/path/to/sum.md', 50)
        
        self.assertIsNotNone(fid1)
        self.assertIsNotNone(fid2)
        
        files = self.tracker.get_files_for_run(run_id)
        self.assertEqual(len(files), 2)
        
        transcript_files = self.tracker.get_files_for_run(run_id, file_type='transcript')
        self.assertEqual(len(transcript_files), 1)
        self.assertEqual(transcript_files[0]['file_path'], '/path/to/trans.srt')
        
    def test_mark_file_deleted(self):
        run_id = self.tracker.start_run('youtube', 'url', 'test_vid')
        fid1 = self.tracker.register_file(run_id, 'transcript', '/path/to/trans.srt', 100)
        
        files = self.tracker.get_files_for_run(run_id)
        self.assertEqual(len(files), 1)
        
        self.tracker.mark_file_deleted(fid1)
        
        files = self.tracker.get_files_for_run(run_id)
        self.assertEqual(len(files), 0)
        
    def test_update_github_url(self):
        run_id = self.tracker.start_run('youtube', 'url', 'test_vid')
        fid1 = self.tracker.register_file(run_id, 'report', '/path/to/report.md', 100)
        
        self.tracker.update_file_github_url(fid1, 'https://github.com/test')
        
        files = self.tracker.get_files_for_run(run_id)
        self.assertEqual(files[0]['github_url'], 'https://github.com/test')

    def test_find_latest_completed_report(self):
        import time
        run_id1 = self.tracker.start_run('youtube', 'url', 'my_video')
        self.tracker.update_status(run_id1, 'COMPLETED', stage='done')
        fid1 = self.tracker.register_file(run_id1, 'report', '/path/to/report1.md', 100, github_url='url1')
        
        time.sleep(1)
        
        run_id2 = self.tracker.start_run('youtube', 'url', 'my_video')
        self.tracker.update_status(run_id2, 'COMPLETED', stage='done')
        fid2 = self.tracker.register_file(run_id2, 'report', '/path/to/report2.md', 100, github_url='url2')
        
        run_id3 = self.tracker.start_run('youtube', 'url', 'my_video')
        self.tracker.update_status(run_id3, 'FAILED', stage='done')
        self.tracker.register_file(run_id3, 'report', '/path/to/report3.md', 100)
        
        res = self.tracker.find_latest_completed_report('my_video')
        self.assertIsNotNone(res)
        self.assertEqual(res['file_path'], '/path/to/report2.md')
        self.assertEqual(res['github_url'], 'url2')

if __name__ == '__main__':
    unittest.main()
