"""Tests for issue 02: dedup DB + migration + local hash + --force.

No real API calls: pipeline download/transcribe paths are stubbed out or
asserted unreachable via the reuse shortcut.
"""

import sqlite3
import tempfile
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.database import DatabaseManager
from src.run_tracker import (
    FAILED_STATUSES,
    find_completed_video,
    get_dedup_db,
    init_videos_table,
    local_content_id,
    mark_video_completed,
    mark_video_failed,
    migrate_legacy_db,
)


def _make_db(tmpdir: str) -> DatabaseManager:
    db = DatabaseManager(Path(tmpdir) / "dedup.db")
    init_videos_table(db)
    return db


class TestVideosSchema(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.db = _make_db(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_schema_columns(self):
        cols = {r['name'] for r in self.db.execute("PRAGMA table_info(videos)")}
        self.assertEqual(
            cols,
            {'video_id', 'url', 'channel_url', 'publish_date', 'first_seen',
             'md_path', 'github_url', 'status', 'fail_count', 'last_error',
             'updated_at', 'uploader', 'title', 'duration_seconds'},
        )

    def test_failed_statuses_is_single_tuple(self):
        self.assertIsInstance(FAILED_STATUSES, tuple)
        self.assertEqual(
            set(FAILED_STATUSES),
            {'DOWNLOAD_FAILED', 'TRANSCRIBE_FAILED', 'SUMMARIZE_FAILED',
             'SUMMARY_FAILED', 'UPLOAD_FAILED', 'failed'},
        )

    def test_completed_roundtrip_and_failed_ignored(self):
        mark_video_completed(self.db, 'vid1', 'http://x/vid1', md_path='/tmp/a.md')
        row = find_completed_video(self.db, 'vid1')
        self.assertIsNotNone(row)
        self.assertEqual(row['md_path'], '/tmp/a.md')
        mark_video_failed(self.db, 'vid2', 'http://x/vid2', 'boom')
        self.assertIsNone(find_completed_video(self.db, 'vid2'))
        fail = self.db.execute_one("SELECT * FROM videos WHERE video_id = 'vid2'")
        self.assertEqual(fail['status'], 'FAILED')
        self.assertEqual(fail['fail_count'], 1)
        self.assertEqual(fail['last_error'], 'boom')

    def test_first_seen_preserved_on_recomplete(self):
        mark_video_completed(self.db, 'vid1', 'http://x/vid1', md_path='/tmp/a.md')
        first = self.db.execute_one("SELECT first_seen FROM videos WHERE video_id='vid1'")['first_seen']
        mark_video_completed(self.db, 'vid1', 'http://x/vid1', md_path='/tmp/b.md')
        row = self.db.execute_one("SELECT * FROM videos WHERE video_id='vid1'")
        self.assertEqual(row['first_seen'], first)
        self.assertEqual(row['md_path'], '/tmp/b.md')


class TestLocalContentId(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _mp3(self, name, content: bytes) -> Path:
        p = self.dir / name
        p.write_bytes(content)
        return p

    def test_stable_and_prefixed(self):
        p = self._mp3('a.mp3', b'\x00' * 100 + b'data')
        self.assertEqual(local_content_id(p), local_content_id(p))
        self.assertTrue(local_content_id(p).startswith('local_'))

    def test_rename_does_not_change_id(self):
        p1 = self._mp3('a.mp3', b'hello audio')
        p2 = self.dir / 'renamed.mp3'
        p1.rename(p2)
        self.assertEqual(local_content_id(self.dir / 'renamed.mp3'),
                         local_content_id(p2))

    def test_content_change_changes_id(self):
        p = self._mp3('a.mp3', b'version one!')
        before = local_content_id(p)
        p.write_bytes(b'version two!')
        self.assertNotEqual(before, local_content_id(p))


class TestMigrateLegacyDb(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.new = self.dir / 'new.db'
        self.old = self.dir / 'run_track.db'
        self.bak = self.dir / 'run_track_backup.db'

    def tearDown(self):
        self._tmp.cleanup()

    def _make_old_db(self, rows):
        with sqlite3.connect(self.old) as conn:
            conn.execute(
                "CREATE TABLE runs (id INTEGER PRIMARY KEY, identifier TEXT,"
                " url_or_path TEXT, status TEXT, started_at TEXT, updated_at TEXT,"
                " report_path TEXT, github_url TEXT)"
            )
            conn.executemany(
                "INSERT INTO runs (identifier, url_or_path, status, started_at,"
                " updated_at, report_path, github_url) VALUES (?,?,?,?,?,?,?)",
                rows,
            )
            conn.commit()

    def _migrate(self):
        return migrate_legacy_db(new_db_path=self.new, old_db_path=self.old,
                                 backup_db_path=self.bak)

    def test_rename_and_import_completed_only(self):
        self._make_old_db([
            ('vidA', 'http://x/A', 'COMPLETED', '2026-09-01 01:00:00',
             '2026-09-01 02:00:00', '/md/a.md', 'https://gh/a'),
            ('vidB', 'http://x/B', 'DOWNLOAD_FAILED', '2026-09-01 01:00:00',
             '2026-09-01 02:00:00', None, None),
        ])
        stats = self._migrate()
        self.assertTrue(stats['renamed'])
        self.assertTrue(self.bak.exists())
        self.assertFalse(self.old.exists())
        db = DatabaseManager(self.new)
        rows = db.execute("SELECT * FROM videos")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['video_id'], 'vidA')
        self.assertEqual(rows[0]['md_path'], '/md/a.md')
        self.assertEqual(rows[0]['github_url'], 'https://gh/a')

    def test_idempotent_rerun(self):
        self._make_old_db([
            ('vidA', 'http://x/A', 'COMPLETED', '2026-09-01 01:00:00',
             '2026-09-01 02:00:00', '/md/a.md', None),
        ])
        self._migrate()
        stats2 = self._migrate()
        self.assertFalse(stats2['renamed'])
        db = DatabaseManager(self.new)
        rows = db.execute("SELECT * FROM videos")
        self.assertEqual(len(rows), 1)

    def test_no_old_db_is_noop(self):
        stats = self._migrate()
        self.assertEqual(stats, {'renamed': False, 'imported': 0})
        db = DatabaseManager(self.new)
        self.assertEqual(db.execute("SELECT COUNT(*) AS n FROM videos")[0]['n'], 0)


class TestPipelineReuse(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.db = _make_db(self._tmp.name)
        self.md = self.dir / 'report.md'
        self.md.write_text('# Report\n')
        self._patch_db = patch('src.pipeline.get_dedup_db', return_value=self.db)
        self._patch_db.start()
        self._patch_log = patch('src.pipeline.log_failure')
        self._patch_log.start()

    def tearDown(self):
        self._patch_db.stop()
        self._patch_log.stop()
        self._tmp.cleanup()

    def test_youtube_reuse_skips_download(self):
        from src.pipeline import ProcessingPipeline
        mark_video_completed(self.db, 'abcdefghijk', 'http://x/watch?v=abcdefghijk',
                             md_path=str(self.md), github_url='https://gh/r')
        with patch('src.youtube_handler.process_youtube_video',
                   side_effect=AssertionError('must not be called')):
            pipe = ProcessingPipeline(run_type='youtube',
                                      url_or_path='https://www.youtube.com/watch?v=abcdefghijk',
                                      identifier='')
            res = pipe.run_youtube()
        self.assertTrue(res['reused'])
        self.assertEqual(res['report_file'], self.md)
        self.assertEqual(res['github_url'], 'https://gh/r')

    def test_youtube_force_bypasses_reuse(self):
        from src.pipeline import ProcessingPipeline
        mark_video_completed(self.db, 'abcdefghijk', 'http://x/watch?v=abcdefghijk',
                             md_path=str(self.md))
        with patch('src.youtube_handler.process_youtube_video',
                   side_effect=RuntimeError('forced download')):
            pipe = ProcessingPipeline(run_type='youtube',
                                      url_or_path='https://www.youtube.com/watch?v=abcdefghijk',
                                      identifier='', force=True)
            with self.assertRaises(RuntimeError):
                pipe.run_youtube()
        fail = self.db.execute_one(
            "SELECT * FROM videos WHERE video_id = 'abcdefghijk'")
        self.assertEqual(fail['status'], 'FAILED')
        self.assertIn('forced download', fail['last_error'])

    def test_local_reuse_skips_transcribe(self):
        from src.pipeline import ProcessingPipeline
        mp3 = self.dir / 'talk.mp3'
        mp3.write_bytes(b'fake audio bytes')
        lid = local_content_id(mp3)
        mark_video_completed(self.db, lid, str(mp3), md_path=str(self.md))
        pipe = ProcessingPipeline(run_type='local', url_or_path=str(mp3),
                                  identifier='talk')
        res = pipe.run_local_mp3(mp3)  # must return before touching Whisper
        self.assertTrue(res['reused'])
        self.assertEqual(res['report_file'], self.md)
        self.assertEqual(pipe.identifier, lid)

    def test_missing_md_file_does_not_reuse(self):
        from src.pipeline import ProcessingPipeline
        mark_video_completed(self.db, 'abcdefghijk', 'http://x/watch?v=abcdefghijk',
                             md_path=str(self.dir / 'gone.md'))
        pipe = ProcessingPipeline(run_type='youtube',
                                  url_or_path='https://www.youtube.com/watch?v=abcdefghijk',
                                  identifier='')
        self.assertIsNone(pipe._reuse_hit('abcdefghijk'))


class TestForceFlags(unittest.TestCase):
    def test_force_and_no_reuse_parse(self):
        from src.cli.parser import create_parser
        args = create_parser().parse_args(['-video', 'http://x', '--force'])
        self.assertTrue(args.force)
        args = create_parser().parse_args(['-local', '/tmp', '--no-reuse'])
        self.assertTrue(args.no_reuse)
        args = create_parser().parse_args(['-video', 'http://x'])
        self.assertFalse(args.force)
        self.assertFalse(args.no_reuse)

    def test_get_dedup_db_creates_videos_table(self):
        with TemporaryDirectory() as d:
            db = get_dedup_db(Path(d) / 'sub' / 't.db')
            cols = {r['name'] for r in db.execute("PRAGMA table_info(videos)")}
            self.assertIn('video_id', cols)


if __name__ == '__main__':
    unittest.main()
