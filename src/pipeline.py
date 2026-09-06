"""Unified processing pipeline (Phase 2.7).

``ProcessingPipeline`` encapsulates a single video/audio processing run with
accurate per-stage status tracking and catch-all error handling that sets the
correct *_FAILED status based on which stage was active when the exception
was raised.

Consumers (``main.py``, ``batch.py``) create one pipeline instance per item
and call ``run()``.  Shared resources (``Transcriber``, ``Summarizer``) can be
passed in to avoid reloading the Whisper model for every item in a batch.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import config
from src.run_tracker import (
    log_failure, get_dedup_db, find_completed_video,
    mark_video_completed, mark_video_failed, local_content_id,
)
from src.transcriber import Transcriber, transcribe_video_audio, read_subtitle_file
from src.summarizer import summarize_transcript
from src.utils import extract_video_id, get_file_size_mb
from src.github_handler import upload_to_github

logger = logging.getLogger(__name__)

# Maps the current pipeline stage to the status that should be written on failure.
STAGE_TO_FAILED_STATUS = {
    'download':   'DOWNLOAD_FAILED',
    'transcribe': 'TRANSCRIBE_FAILED',
    'summarize':  'SUMMARIZE_FAILED',
    'upload':     'UPLOAD_FAILED',
}


class ProcessingPipeline:
    """Run the full download → transcribe → summarize → upload pipeline for
    a single YouTube video or local MP3.

    Args:
        run_type: 'youtube' | 'local'
        url_or_path: Original URL or file path string
        identifier: video_id / file stem / episode identifier
        summary_style: 'detailed' | 'brief'
        upload: Whether to upload the report to GitHub
        transcriber: Optional pre-loaded Transcriber instance (avoids reloading model)
        force: Re-run even when the dedup DB has a COMPLETED row (--force/--no-reuse)
    """

    def __init__(
        self,
        run_type: str,
        url_or_path: str,
        identifier: str,
        summary_style: str = "detailed",
        upload: bool = False,
        transcriber: Optional[Transcriber] = None,
        force: bool = False,
    ):
        self.run_type = run_type
        self.url_or_path = url_or_path
        self.identifier = identifier
        self.summary_style = summary_style
        self.upload = upload
        self._shared_transcriber = transcriber
        self.force = force

        self.current_stage: str = "download"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _set_stage(self, stage: str, status: str):
        del status  # terminal state goes to the videos table in _complete/_fail
        self.current_stage = stage

    def _reuse_hit(self, video_id: str) -> Optional[dict]:
        """Return a reused-result dict when the new DB has COMPLETED + existing MD."""
        if self.force or not video_id:
            return None
        try:
            row = find_completed_video(get_dedup_db(), video_id)
        except Exception as e:
            logger.warning("Dedup check skipped (DB unavailable): %s", e)
            return None
        if not row or not row.get('md_path'):
            return None
        md_path = Path(row['md_path'])
        if not md_path.exists():
            return None
        try:
            generated = datetime.fromtimestamp(md_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        except OSError:
            generated = row.get('updated_at') or '?'
        logger.info("Reusing COMPLETED %s → report: %s (generated: %s)",
                    video_id, md_path, generated)
        return {
            'reused': True,
            'report_file': md_path,
            'github_url': row.get('github_url'),
        }

    def _fail(self, error: Exception):
        status = STAGE_TO_FAILED_STATUS.get(self.current_stage, 'DOWNLOAD_FAILED')
        del status
        try:
            mark_video_failed(get_dedup_db(), self.identifier or self.url_or_path,
                              self.url_or_path, str(error))
        except Exception as e:
            logger.warning("Failed to record FAILED state: %s", e)
        log_failure(self.run_type, self.identifier, self.url_or_path, str(error), stage=self.current_stage)

    def _complete(self, transcript_path=None, summary_path=None, report_path=None,
                   github_url=None, model_used=None, audio_path=None, prompt_info=None,
                   publish_date=None, channel_url=None,
                   uploader=None, title=None, duration_seconds=None):
        del transcript_path, summary_path, model_used, audio_path, prompt_info  # legacy runs-table detail; videos table keeps the report pointer
        try:
            mark_video_completed(
                get_dedup_db(), self.identifier, self.url_or_path,
                md_path=str(report_path) if report_path else None,
                github_url=github_url, channel_url=channel_url,
                publish_date=publish_date,
                uploader=uploader, title=title, duration_seconds=duration_seconds,
            )
        except Exception as e:
            logger.warning("Failed to record COMPLETED state: %s", e)

    # ------------------------------------------------------------------
    # Upload helper (shared by all run types)
    # ------------------------------------------------------------------

    def _upload_report(self, report_file: Path, uploader: Optional[str] = None) -> Optional[str]:
        """Upload report to GitHub; returns URL or None on failure."""
        if not self.upload or not report_file:
            return None
        self._set_stage('upload', 'UPLOADING')
        try:
            github_url = upload_to_github(report_file, uploader=uploader, use_category_folder=True)
            if github_url:
                logger.info("GitHub URL: %s", github_url)
            return github_url
        except Exception as e:
            logger.warning("GitHub upload failed: %s", e)
            return None

    # ------------------------------------------------------------------
    # YouTube video pipeline
    # ------------------------------------------------------------------

    def run_youtube(
        self,
        cookies_file: Optional[str] = None,
        cookies_from_browser: bool = False,
        browser: str = "chrome",
        keep_audio: bool = False,
    ) -> dict:
        """Run the full pipeline for a YouTube video."""
        from src.youtube_handler import process_youtube_video  # local import to avoid circularity
        from src.utils import extract_video_id

        if not self.identifier and self.url_or_path:
            vid = extract_video_id(self.url_or_path)
            if vid:
                self.identifier = vid

        try:
            # --- Dedup: reuse COMPLETED row from the new DB (GitHub zero新增) ---
            hit = self._reuse_hit(self.identifier)
            if hit:
                return hit

            # --- download ---
            self.current_stage = 'download'
            logger.info("[1/4] Fetching video information...")
            result = process_youtube_video(
                self.url_or_path,
                cookies_file=cookies_file,
                cookies_from_browser=cookies_from_browser,
                browser=browser,
            )
            video_info = result['info']
            video_id = result['video_id']
            logger.info("  Title: %s", video_info['title'])
            logger.info("  Duration: %ss", video_info['duration'])
            logger.info("  Uploader: %s", video_info['uploader'])

            # --- transcribe ---
            self._set_stage('transcribe', 'DOWNLOADING')
            transcript = None
            audio_path_used = None

            if result['needs_transcription']:
                logger.info("[2/4] Transcribing audio with Whisper...")
                audio_path = result['audio_path']
                audio_path_used = audio_path
                logger.info("  Audio file: %s (%.2f MB)", audio_path, get_file_size_mb(audio_path))
                transcriber = self._shared_transcriber or Transcriber()
                tr_result = transcriber.transcribe_audio(audio_path)
                transcript = transcriber.get_transcript_text(tr_result)
                whisper_language = tr_result.get('language', 'en')
                srt_path = config.TRANSCRIPT_DIR / f"{video_id}_transcript.srt"
                transcriber.save_as_srt(tr_result, srt_path)

                if not keep_audio and not config.KEEP_AUDIO:
                    audio_path.unlink(missing_ok=True)
                    audio_path_used = None
            else:
                logger.info("[2/4] Reading subtitle file...")
                subtitle_path = result['subtitle_path']
                srt_path = subtitle_path
                transcript, whisper_language = read_subtitle_file(subtitle_path)

            logger.info("  Transcript length: %d chars | language: %s", len(transcript), whisper_language)
            self._set_stage('transcribe', 'TRANSCRIPT_READY')

            # --- summarize ---
            logger.info("[3/4] Generating AI summary...")
            self._set_stage('summarize', 'SUMMARIZING')
            summary_result = summarize_transcript(
                transcript, video_id, video_info,
                style=self.summary_style,
                language=config.SUMMARY_LANGUAGE,
                video_url=self.url_or_path,
            )

            # --- upload ---
            report_file = summary_result.get('report_path')
            prompt_info = summary_result.get('prompt_info')
            
            self._set_stage('upload', 'SUMMARY_READY')
            github_url = self._upload_report(report_file, uploader=video_info.get('uploader'))

            logger.info("[4/4] Processing complete!")
            self.identifier = video_id
            self._complete(
                transcript_path=srt_path,
                summary_path=summary_result.get('summary_path'),
                report_path=report_file,
                github_url=github_url,
                audio_path=audio_path_used,
                prompt_info=prompt_info,
                model_used=summary_result.get('model_used'),
                publish_date=video_info.get('upload_date'),
                uploader=video_info.get('uploader'),
                title=video_info.get('title'),
                duration_seconds=video_info.get('duration'),
            )

            return {
                'video_id': video_id,
                'video_info': video_info,
                'transcript': transcript,
                'transcript_file': srt_path,
                'summary_file': summary_result.get('summary_path'),
                'report_file': report_file,
                'github_url': github_url,
            }

        except Exception as e:
            logger.error("Processing failed: %s", e)
            logger.debug("Error details", exc_info=True)
            self._fail(e)
            raise

    # ------------------------------------------------------------------
    # Local MP3 pipeline
    # ------------------------------------------------------------------

    def run_local_mp3(self, mp3_path: Path) -> dict:
        """Run the full pipeline for a local MP3 file.

        Dedup key is the content hash (rename-proof); url stores the original path.
        """
        try:
            self.identifier = local_content_id(mp3_path)

            # --- Dedup: reuse COMPLETED row from the new DB (GitHub zero新增) ---
            hit = self._reuse_hit(self.identifier)
            if hit:
                return hit

            logger.info("  File: %s (%.2f MB)", mp3_path.name, get_file_size_mb(mp3_path))

            # --- transcribe ---
            self._set_stage('transcribe', 'AUDIO_DOWNLOADED')
            logger.info("[1/3] Transcribing audio with Whisper...")
            transcriber = self._shared_transcriber or Transcriber()
            tr_result = transcriber.transcribe_audio(mp3_path)
            transcript = transcriber.get_transcript_text(tr_result)
            whisper_language = tr_result.get('language', 'en')

            srt_path = config.TRANSCRIPT_DIR / f"{self.identifier}_transcript.srt"
            transcriber.save_as_srt(tr_result, srt_path)
            logger.info("  Transcript length: %d chars | language: %s", len(transcript), whisper_language)
            self._set_stage('transcribe', 'TRANSCRIPT_READY')

            # --- summarize ---
            logger.info("[2/3] Generating AI summary...")
            self._set_stage('summarize', 'SUMMARIZING')
            video_info = {
                'title': Path(mp3_path).stem,
                'uploader': 'Local Audio',
                'duration': int(tr_result.get('segments', [{}])[-1].get('end', 0)) if tr_result.get('segments') else 0,
            }
            summary_result = summarize_transcript(
                transcript, self.identifier, video_info,
                style=self.summary_style,
                language=config.SUMMARY_LANGUAGE,
                video_url=None,
            )

            # --- upload ---
            report_file = summary_result.get('report_path')
            prompt_info = summary_result.get('prompt_info')
            
            self._set_stage('upload', 'SUMMARY_READY')
            github_url = self._upload_report(report_file, uploader='Local Audio')

            logger.info("[3/3] Processing complete!")
            self._complete(
                transcript_path=srt_path,
                summary_path=summary_result.get('summary_path'),
                report_path=report_file,
                github_url=github_url,
                prompt_info=prompt_info,
                model_used=summary_result.get('model_used'),
                uploader=video_info.get('uploader'),
                title=video_info.get('title'),
                duration_seconds=video_info.get('duration'),
            )

            return {
                'file_name': self.identifier,
                'file_path': mp3_path,
                'transcript': transcript,
                'transcript_file': srt_path,
                'summary_file': summary_result.get('summary_path'),
                'report_file': report_file,
                'github_url': github_url,
            }

        except Exception as e:
            logger.error("Processing failed: %s", e)
            logger.debug("Error details", exc_info=True)
            self._fail(e)
            raise

    # ------------------------------------------------------------------
    # Smart resume (Phase 2.4)
    # ------------------------------------------------------------------

    @staticmethod
    def resume(run: dict, summary_style: str = "detailed", upload: bool = False) -> dict:
        """Resume a stalled run based on its current status.

        Strategy:
          DOWNLOAD_FAILED               → fully re-process (caller must re-call
                                          run_youtube / run_local_mp3 with the URL)
          TRANSCRIBE_FAILED             → re-transcribe if audio exists, else fail
          TRANSCRIPT_READY / SUMMARIZE_FAILED / SUMMARY_FAILED
                                        → re-summarize from existing SRT
          SUMMARY_READY / UPLOAD_FAILED → re-upload existing report
        """
        from src.run_tracker import RunTracker, get_tracker  # noqa: PLC0415
        tracker = get_tracker()
        status = run.get('status', '')
        run_id = run['id']
        identifier = run['identifier']
        url_or_path = run.get('url_or_path', '')

        resume_stage = RunTracker.RESUMABLE_STATUS_MAP.get(status)
        if not resume_stage:
            logger.warning("Run %s (status=%s) is not resumable", run_id, status)
            return {'skipped': True, 'run_id': run_id}

        logger.info("Resuming run %s (status=%s → stage=%s)", run_id, status, resume_stage)
        tracker.increment_retry(run_id)

        if resume_stage == 'download':
            # Nothing we can do without the caller re-supplying the URL
            logger.warning("Run %s must be fully re-processed (DOWNLOAD_FAILED)", run_id)
            return {'error': 'Must re-process from download stage', 'run_id': run_id}

        if resume_stage == 'transcribe':
            audio_path = run.get('audio_path')
            if not audio_path or not Path(audio_path).exists():
                logger.warning("Audio file missing for run %s; cannot re-transcribe", run_id)
                tracker.update_status(run_id, 'DOWNLOAD_FAILED',
                                      'Audio file missing; must re-download', stage='download')
                return {'error': 'Audio file missing', 'run_id': run_id}
            # Re-transcribe
            try:
                tracker.update_status(run_id, 'TRANSCRIBING', stage='transcribe')
                transcriber = Transcriber()
                tr_result = transcriber.transcribe_audio(Path(audio_path))
                transcript = transcriber.get_transcript_text(tr_result)
                srt_path = config.TRANSCRIPT_DIR / f"{identifier}_transcript.srt"
                transcriber.save_as_srt(tr_result, srt_path)
                tracker.update_status(run_id, 'TRANSCRIPT_READY', stage='transcribe')
                tracker.update_artifacts(run_id, transcript_path=str(srt_path))
                # fall through to summarize
            except Exception as e:
                tracker.update_status(run_id, 'TRANSCRIBE_FAILED', str(e), stage='transcribe')
                return {'error': str(e), 'run_id': run_id}
        else:
            # Read existing SRT
            srt_path = Path(run.get('transcript_path') or
                            config.TRANSCRIPT_DIR / f"{identifier}_transcript.srt")
            if not srt_path.exists():
                logger.warning("SRT not found for run %s: %s", run_id, srt_path)
                tracker.update_status(run_id, 'TRANSCRIBE_FAILED',
                                      f'Missing SRT: {srt_path}', stage='transcribe')
                return {'error': f'Missing SRT: {srt_path}', 'run_id': run_id}
            transcript, _ = read_subtitle_file(srt_path)

        if resume_stage in ('transcribe', 'summarize'):
            try:
                tracker.update_status(run_id, 'SUMMARIZING', stage='summarize')
                video_info = {'title': identifier, 'uploader': '', 'duration': 0}
                video_url = url_or_path if url_or_path.startswith('http') else None
                summary_result = summarize_transcript(
                    transcript, identifier, video_info,
                    style=summary_style,
                    language=config.SUMMARY_LANGUAGE,
                    video_url=video_url,
                )
                report_file = summary_result.get('report_path')
                prompt_info = summary_result.get('prompt_info')
                
                tracker.update_status(run_id, 'SUMMARY_READY', stage='summarize')
                
                updates = {
                    "summary_path": str(summary_result.get('summary_path')),
                    "report_path": str(report_file) if report_file else None,
                }
                if prompt_info:
                    updates.update({
                        "prompt_type": prompt_info.get("prompt_type"),
                        "prompt_source": prompt_info.get("prompt_source"),
                        "prompt_index": prompt_info.get("prompt_index"),
                        "prompt_file": prompt_info.get("prompt_file"),
                    })
                model_used = summary_result.get('model_used')
                if model_used:
                    updates["model_used"] = model_used

                tracker.update_artifacts(run_id, **updates)
            except Exception as e:
                tracker.update_status(run_id, 'SUMMARIZE_FAILED', str(e), stage='summarize')
                return {'error': str(e), 'run_id': run_id}
        else:
            report_file = Path(run.get('report_path', '')) if run.get('report_path') else None

        if resume_stage in ('transcribe', 'summarize', 'upload') and upload and report_file:
            if report_file.exists():
                try:
                    tracker.update_status(run_id, 'UPLOADING', stage='upload')
                    # Find uploader from file_storage or just run
                    # We can use a basic fallback wrapper
                    run_info = tracker.get_run_info(run_id) or {}
                    github_url = upload_to_github(report_file, uploader="Resumed")
                    tracker.update_status(run_id, 'COMPLETED', error_message=None, stage='done')
                    tracker.update_artifacts(run_id, github_url=github_url)
                    return {'success': True, 'run_id': run_id, 'github_url': github_url}
                except Exception as e:
                    tracker.update_status(run_id, 'UPLOAD_FAILED', str(e), stage='upload')
                    return {'error': str(e), 'run_id': run_id}
            else:
                logger.warning("Report file not found for upload: %s", report_file)

        tracker.update_status(run_id, 'COMPLETED', error_message=None, stage='done')
        return {'success': True, 'run_id': run_id}
