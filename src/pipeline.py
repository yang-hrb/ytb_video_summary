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
from pathlib import Path
from typing import Optional

from config import config
from src.run_tracker import get_tracker, log_failure
from src.transcriber import Transcriber, transcribe_video_audio, read_subtitle_file
from src.summarizer import summarize_transcript
from src.utils import get_file_size_mb
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
    a single YouTube video, local MP3, or podcast episode.

    Args:
        run_type: 'youtube' | 'local' | 'podcast'
        url_or_path: Original URL or file path string
        identifier: video_id / file stem / episode identifier
        summary_style: 'detailed' | 'brief'
        upload: Whether to upload the report to GitHub
        transcriber: Optional pre-loaded Transcriber instance (avoids reloading model)
    """

    def __init__(
        self,
        run_type: str,
        url_or_path: str,
        identifier: str,
        summary_style: str = "detailed",
        upload: bool = False,
        transcriber: Optional[Transcriber] = None,
    ):
        self.run_type = run_type
        self.url_or_path = url_or_path
        self.identifier = identifier
        self.summary_style = summary_style
        self.upload = upload
        self._shared_transcriber = transcriber

        self.tracker = get_tracker()
        self.run_id: Optional[int] = None
        self.current_stage: str = "download"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _start(self):
        self.run_id = self.tracker.start_run(
            self.run_type, self.url_or_path, self.identifier
        )
        self.tracker.update_status(self.run_id, 'PENDING', stage='download')
        logger.debug("Pipeline started: run_id=%s identifier=%s", self.run_id, self.identifier)

    def _set_stage(self, stage: str, status: str):
        self.current_stage = stage
        if self.run_id:
            self.tracker.update_status(self.run_id, status, stage=stage)

    def _fail(self, error: Exception):
        status = STAGE_TO_FAILED_STATUS.get(self.current_stage, 'DOWNLOAD_FAILED')
        if self.run_id:
            self.tracker.update_status(self.run_id, status, str(error), stage=self.current_stage)
        log_failure(self.run_type, self.identifier, self.url_or_path, str(error), stage=self.current_stage)

    def _complete(self, transcript_path=None, summary_path=None, report_path=None,
                  github_url=None, model_used=None, audio_path=None):
        if self.run_id:
            self.tracker.update_status(self.run_id, 'COMPLETED', error_message=None, stage='done')
            self.tracker.update_artifacts(
                self.run_id,
                transcript_path=str(transcript_path) if transcript_path else None,
                summary_path=str(summary_path) if summary_path else None,
                report_path=str(report_path) if report_path else None,
                github_url=github_url,
                model_used=model_used,
                audio_path=str(audio_path) if audio_path else None,
                summary_style=self.summary_style,
            )

    # ------------------------------------------------------------------
    # Upload helper (shared by all run types)
    # ------------------------------------------------------------------

    def _upload_report(self, report_file: Path) -> Optional[str]:
        """Upload report to GitHub; returns URL or None on failure."""
        if not self.upload or not report_file:
            return None
        self._set_stage('upload', 'UPLOADING')
        try:
            github_url = upload_to_github(report_file)
            if github_url:
                logger.info("GitHub URL: %s", github_url)
            return github_url
        except Exception as e:
            logger.warning("GitHub upload failed: %s", e)
            if self.run_id:
                self.tracker.update_status(
                    self.run_id, 'UPLOAD_FAILED', str(e), stage='upload'
                )
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

        self._start()
        try:
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
            self._set_stage('upload', 'SUMMARY_READY')
            github_url = self._upload_report(report_file)

            logger.info("[4/4] Processing complete!")
            self._complete(
                transcript_path=srt_path,
                summary_path=summary_result.get('summary_path'),
                report_path=report_file,
                github_url=github_url,
                audio_path=audio_path_used,
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
        """Run the full pipeline for a local MP3 file."""
        self._start()
        try:
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
                'title': self.identifier,
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
            self._set_stage('upload', 'SUMMARY_READY')
            github_url = self._upload_report(report_file)

            logger.info("[3/3] Processing complete!")
            self._complete(
                transcript_path=srt_path,
                summary_path=summary_result.get('summary_path'),
                report_path=report_file,
                github_url=github_url,
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
    # Podcast episode pipeline
    # ------------------------------------------------------------------

    def run_podcast(self, audio_path: Path, video_info: dict) -> dict:
        """Run summarize → upload for a pre-downloaded podcast episode.

        Transcription is expected to be done before calling this method
        (audio_path points to the downloaded episode).  However, the full
        transcription stage is handled here so the stage tracker is accurate.
        """
        self._start()
        try:
            logger.info("  Audio: %s (%.2f MB)", audio_path, get_file_size_mb(audio_path))

            # --- transcribe ---
            self._set_stage('transcribe', 'AUDIO_DOWNLOADED')
            logger.info("[2/3] Transcribing audio with Whisper...")
            transcriber = self._shared_transcriber or Transcriber()
            tr_result = transcriber.transcribe_audio(audio_path)
            transcript = transcriber.get_transcript_text(tr_result)
            whisper_language = tr_result.get('language', 'en')

            srt_path = config.TRANSCRIPT_DIR / f"{self.identifier}_transcript.srt"
            transcriber.save_as_srt(tr_result, srt_path)

            if not config.KEEP_AUDIO:
                audio_path.unlink(missing_ok=True)

            logger.info("  Transcript length: %d chars | language: %s", len(transcript), whisper_language)
            self._set_stage('transcribe', 'TRANSCRIPT_READY')

            # --- summarize ---
            logger.info("[3/3] Generating AI summary...")
            self._set_stage('summarize', 'SUMMARIZING')
            summary_result = summarize_transcript(
                transcript, self.identifier, video_info,
                style=self.summary_style,
                language=config.SUMMARY_LANGUAGE,
                video_url=self.url_or_path,
            )

            # --- upload ---
            report_file = summary_result.get('report_path')
            self._set_stage('upload', 'SUMMARY_READY')
            github_url = self._upload_report(report_file)

            logger.info("[Done] Processing complete!")
            self._complete(
                transcript_path=srt_path,
                summary_path=summary_result.get('summary_path'),
                report_path=report_file,
                github_url=github_url,
            )

            return {
                'identifier': self.identifier,
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
        from src.run_tracker import RunTracker  # noqa: PLC0415
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
                tracker.update_status(run_id, 'SUMMARY_READY', stage='summarize')
                tracker.update_artifacts(
                    run_id,
                    summary_path=str(summary_result.get('summary_path')),
                    report_path=str(report_file) if report_file else None,
                )
            except Exception as e:
                tracker.update_status(run_id, 'SUMMARIZE_FAILED', str(e), stage='summarize')
                return {'error': str(e), 'run_id': run_id}
        else:
            report_file = Path(run.get('report_path', '')) if run.get('report_path') else None

        if resume_stage in ('transcribe', 'summarize', 'upload') and upload and report_file:
            if report_file.exists():
                try:
                    tracker.update_status(run_id, 'UPLOADING', stage='upload')
                    github_url = upload_to_github(report_file)
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
