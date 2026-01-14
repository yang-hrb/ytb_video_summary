"""Web server for running YouTube summarization jobs."""

from __future__ import annotations

import asyncio
import json
import os
import queue
import subprocess
import sys
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterable, Deque, Dict, Iterable, List, Optional, Set, Tuple

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils import is_playlist_url


LOG_BUFFER_SIZE = 500
HISTORY_PATH = _PROJECT_ROOT / "server" / "job_history.json"


class JobCreateRequest(BaseModel):
    """Request body for creating a job."""

    url: str
    style: str = "detailed"
    upload: bool = True


@dataclass
class Job:
    """Represents a single background job."""

    job_id: str
    url: str
    style: str
    upload: bool
    is_playlist: bool
    status: str = "queued"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    exit_code: Optional[int] = None
    output_paths: List[str] = field(default_factory=list)
    logs: Deque[str] = field(default_factory=lambda: deque(maxlen=LOG_BUFFER_SIZE))
    all_logs: List[str] = field(default_factory=list)
    process: Optional[subprocess.Popen[str]] = None
    cancel_requested: bool = False
    subscribers: Set[queue.Queue[Tuple[str, str]]] = field(default_factory=set)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def append_log(self, line: str) -> None:
        """Append a log line and notify subscribers."""
        with self.lock:
            self.logs.append(line)
            self.all_logs.append(line)
            subscribers = list(self.subscribers)
        for subscriber in subscribers:
            subscriber.put(("log", line))

    def set_status(self, status: str, exit_code: Optional[int] = None) -> None:
        """Update status and notify subscribers."""
        with self.lock:
            self.status = status
            if exit_code is not None:
                self.exit_code = exit_code
            if status in {"succeeded", "failed", "canceled"}:
                self.ended_at = datetime.now(timezone.utc)
            subscribers = list(self.subscribers)
        payload = {
            "status": self.status,
            "exit_code": self.exit_code,
            "started_at": _format_dt(self.started_at),
            "ended_at": _format_dt(self.ended_at),
        }
        data = json.dumps(payload)
        for subscriber in subscribers:
            subscriber.put(("status", data))

    def subscribe(self) -> queue.Queue[Tuple[str, str]]:
        """Register a new SSE subscriber queue."""
        subscriber: queue.Queue[Tuple[str, str]] = queue.Queue()
        with self.lock:
            self.subscribers.add(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: queue.Queue[Tuple[str, str]]) -> None:
        """Remove an SSE subscriber queue."""
        with self.lock:
            self.subscribers.discard(subscriber)


class JobRegistry:
    """In-memory job registry with optional persistence."""

    def __init__(self, history_path: Path) -> None:
        self._history_path = history_path
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()
        self._load_history()

    def _load_history(self) -> None:
        if not self._history_path.exists():
            return
        try:
            records = json.loads(self._history_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        for record in records:
            created_at = _parse_dt(record.get("created_at"))
            started_at = _parse_dt(record.get("started_at"))
            ended_at = _parse_dt(record.get("ended_at"))
            job = Job(
                job_id=record["job_id"],
                url=record["url"],
                style=record.get("style", "detailed"),
                upload=record.get("upload", True),
                is_playlist=record.get("is_playlist", False),
                status=record.get("status", "queued"),
                created_at=created_at or datetime.now(timezone.utc),
                started_at=started_at,
                ended_at=ended_at,
                exit_code=record.get("exit_code"),
                output_paths=record.get("output_paths", []),
            )
            self._jobs[job.job_id] = job

    def _persist_history(self) -> None:
        records = [self._serialize_job(job) for job in self._jobs.values()]
        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        self._history_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _serialize_job(self, job: Job) -> Dict[str, object]:
        return {
            "job_id": job.job_id,
            "url": job.url,
            "style": job.style,
            "upload": job.upload,
            "is_playlist": job.is_playlist,
            "status": job.status,
            "created_at": _format_dt(job.created_at),
            "started_at": _format_dt(job.started_at),
            "ended_at": _format_dt(job.ended_at),
            "exit_code": job.exit_code,
            "output_paths": job.output_paths,
        }

    def create_job(self, request: JobCreateRequest) -> Job:
        """Create a new job and persist it."""
        job_id = uuid.uuid4().hex
        job = Job(
            job_id=job_id,
            url=request.url,
            style=request.style,
            upload=request.upload,
            is_playlist=is_playlist_url(request.url),
        )
        with self._lock:
            self._jobs[job_id] = job
            self._persist_history()
        return job

    def get_job(self, job_id: str) -> Job:
        """Get a job by ID."""
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        return job

    def list_jobs(self, limit: int) -> List[Job]:
        """Return recent jobs sorted by creation time."""
        with self._lock:
            jobs = list(self._jobs.values())
        jobs.sort(key=lambda job: job.created_at, reverse=True)
        return jobs[:limit]

    def persist(self, job: Job) -> None:
        """Persist a job record to disk."""
        with self._lock:
            self._jobs[job.job_id] = job
            self._persist_history()


load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")

app = FastAPI()
registry = JobRegistry(HISTORY_PATH)

web_dir = _PROJECT_ROOT / "web"
app.mount("/static", StaticFiles(directory=web_dir), name="static")


@app.get("/")
def read_index() -> FileResponse:
    """Serve the single-page UI."""
    return FileResponse(web_dir / "index.html")


@app.post("/api/jobs")
def create_job(request: JobCreateRequest) -> Dict[str, str]:
    """Create a new background job."""
    job = registry.create_job(request)
    job.append_log(f"[UI] Job created for {job.url}")
    thread = threading.Thread(target=_run_job, args=(job,), daemon=True)
    thread.start()
    return {"job_id": job.job_id}


@app.get("/api/jobs")
def list_jobs(limit: int = 20) -> List[Dict[str, object]]:
    """List recent jobs."""
    jobs = registry.list_jobs(limit)
    return [_job_summary(job) for job in jobs]


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> Dict[str, object]:
    """Return job metadata."""
    try:
        job = registry.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    return _job_detail(job)


@app.get("/api/jobs/{job_id}/events")
def stream_job_events(job_id: str, request: Request) -> StreamingResponse:
    """Stream job logs and status updates via SSE."""
    try:
        job = registry.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc

    async def event_stream() -> AsyncIterable[str]:
        subscriber = job.subscribe()
        try:
            with job.lock:
                backlog = list(job.logs)
            for line in backlog:
                yield _format_sse("log", line)
            payload = {
                "status": job.status,
                "exit_code": job.exit_code,
                "started_at": _format_dt(job.started_at),
                "ended_at": _format_dt(job.ended_at),
            }
            yield _format_sse("status", json.dumps(payload))
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event_type, data = await asyncio.to_thread(
                        subscriber.get, True, 0.5
                    )
                except queue.Empty:
                    yield ": keep-alive\n\n"
                    continue
                yield _format_sse(event_type, data)
        finally:
            job.unsubscribe(subscriber)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> Dict[str, str]:
    """Cancel a running job."""
    try:
        job = registry.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc

    if job.status not in {"running", "queued"}:
        return {"status": job.status}

    job.cancel_requested = True
    job.append_log("[UI] Cancel requested...")
    process = job.process
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    exit_code = process.returncode if process is not None else None
    job.set_status("canceled", exit_code=exit_code)
    registry.persist(job)
    return {"status": job.status}


@app.get("/api/jobs/{job_id}/log")
def download_log(job_id: str) -> PlainTextResponse:
    """Download job logs as plain text."""
    try:
        job = registry.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    log_text = "\n".join(job.all_logs)
    headers = {
        "Content-Disposition": f"attachment; filename=job_{job.job_id}.log"
    }
    return PlainTextResponse(log_text, headers=headers)


def _run_job(job: Job) -> None:
    """Execute the CLI job in a background thread."""
    if job.cancel_requested:
        job.set_status("canceled")
        registry.persist(job)
        return
    job.started_at = datetime.now(timezone.utc)
    job.set_status("running")
    command = _build_command(job)
    job.append_log(f"[UI] Running: {' '.join(command)}")
    try:
        process = subprocess.Popen(
            command,
            cwd=str(_PROJECT_ROOT),
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except OSError as exc:
        job.append_log(f"[UI] Failed to start process: {exc}")
        job.set_status("failed")
        registry.persist(job)
        return

    job.process = process
    stdout_thread = threading.Thread(
        target=_stream_output, args=(job, process.stdout, ""), daemon=True
    )
    stderr_thread = threading.Thread(
        target=_stream_output, args=(job, process.stderr, "[stderr] "), daemon=True
    )
    stdout_thread.start()
    stderr_thread.start()

    exit_code = process.wait()
    stdout_thread.join(timeout=1)
    stderr_thread.join(timeout=1)

    if job.cancel_requested:
        job.set_status("canceled", exit_code=exit_code)
    elif exit_code == 0:
        job.set_status("succeeded", exit_code=exit_code)
    else:
        job.set_status("failed", exit_code=exit_code)

    registry.persist(job)


def _stream_output(job: Job, stream: Optional[Iterable[str]], prefix: str) -> None:
    """Stream subprocess output into the job logs."""
    if stream is None:
        return
    for line in stream:
        cleaned = line.rstrip("\n")
        if cleaned:
            job.append_log(f"{prefix}{cleaned}")


def _build_command(job: Job) -> List[str]:
    """Build the CLI command for a job."""
    command = [sys.executable, "src/main.py"]
    if job.is_playlist:
        command.extend(["-list", job.url])
    else:
        command.extend(["-video", job.url])
    if job.style:
        command.extend(["--style", job.style])
    if job.upload:
        command.append("--upload")
    return command


def _job_summary(job: Job) -> Dict[str, object]:
    """Return summary metadata for job history list."""
    return {
        "job_id": job.job_id,
        "url": job.url,
        "is_playlist": job.is_playlist,
        "status": job.status,
        "created_at": _format_dt(job.created_at),
        "started_at": _format_dt(job.started_at),
        "ended_at": _format_dt(job.ended_at),
        "exit_code": job.exit_code,
    }


def _job_detail(job: Job) -> Dict[str, object]:
    """Return detailed metadata for a job."""
    detail = _job_summary(job)
    detail.update(
        {
            "style": job.style,
            "upload": job.upload,
            "output_paths": job.output_paths,
        }
    )
    return detail


def _format_dt(value: Optional[datetime]) -> Optional[str]:
    """Format datetime values for JSON output."""
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat()


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    """Parse datetime values from JSON."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _format_sse(event_type: str, data: str) -> str:
    """Format SSE payload."""
    safe_data = data.replace("\r", "")
    return f"event: {event_type}\ndata: {safe_data}\n\n"


def main() -> None:
    """Run the FastAPI application with Uvicorn."""
    uvicorn.run("server.app:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
