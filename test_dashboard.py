import sys
import os
import requests
import time
import subprocess

if not os.path.exists("venv"):
    print("Wait, no venv?")
else:
    proc = subprocess.Popen(["venv/bin/uvicorn", "src.dashboard_app:app", "--host", "127.0.0.1", "--port", "8080"])
    try:
        time.sleep(3) 

        print("Testing /api/runs")
        r = requests.get("http://127.0.0.1:8080/api/runs?page=1&page_size=10")
        print("Runs code:", r.status_code)

        print("Testing /api/stats")
        r = requests.get("http://127.0.0.1:8080/api/stats")
        print("Stats code:", r.status_code)

        print("Testing Dashboard HTML")
        r = requests.get("http://127.0.0.1:8080/dashboard")
        print("HTML code:", r.status_code)

        print("Testing Playlist Job Submit (mock)")
        job_payload = {"playlist_url": "https://www.youtube.com/playlist?list=PL_foo"}
        r = requests.post("http://127.0.0.1:8080/api/jobs/playlist", json=job_payload)
        print("Post code:", r.status_code)
        resp = r.json()
        print("Post Response:", resp)
        
        job_id = resp.get("job_id")
        print("Waiting to see if it finishes the job... job_id=", job_id)
        time.sleep(5)
        
        r2 = requests.get(f"http://127.0.0.1:8080/api/jobs/{job_id}")
        data = r2.json()
        print("Job Status:", data.get("status"))
        if data.get("zip_path"):
            print("Zip created:", os.path.basename(data.get("zip_path")))
    except Exception as e:
        print("Failed:", e)
    finally:
        proc.terminate()
