from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
import os

from src.dashboard_service import DashboardService
from src.job_manager import JobManager
from src.zip_exporter import ZipExporter

app = FastAPI(title="YTB Video Summary Dashboard")

service = DashboardService()
job_manager = JobManager()
zip_exporter = ZipExporter()

# Ensure web directory exists
os.makedirs("web", exist_ok=True)
if os.path.exists("web"):
    app.mount("/static", StaticFiles(directory="web"), name="static")

class PlaylistJobRequest(BaseModel):
    playlist_url: str
    api_key: Optional[str] = None
    summary_style: Optional[str] = "detailed"
    github_upload: Optional[bool] = False

@app.get("/dashboard")
async def get_dashboard():
    dashboard_path = "web/dashboard.html"
    if not os.path.exists(dashboard_path):
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return FileResponse(dashboard_path)

@app.get("/api/runs")
async def get_runs(page: int = 1, page_size: int = 10, uploader: Optional[str] = None, 
                   status: Optional[str] = None, search: Optional[str] = None):
    return service.get_runs(page, page_size, uploader, status, search)

@app.get("/api/stats")
async def get_stats():
    return service.get_stats()

@app.post("/api/jobs/playlist")
async def create_playlist_job(request: PlaylistJobRequest, background_tasks: BackgroundTasks):
    job_id = job_manager.create_job(request.playlist_url, request.summary_style)
    background_tasks.add_task(job_manager.run_playlist_job, job_id, request.playlist_url, 
                              request.api_key, request.summary_style, request.github_upload)
    return {"job_id": job_id, "status": "queued"}

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/api/jobs/{job_id}/zip")
async def download_job_zip(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.get("zip_path") or not os.path.exists(job["zip_path"]):
        raise HTTPException(status_code=404, detail="ZIP file not ready or not found")
    return FileResponse(job["zip_path"], filename=f"summary_bundle_{job_id}.zip")
