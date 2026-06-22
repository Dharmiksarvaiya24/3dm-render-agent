# ===== controller/api.py =====

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from controller.job_queue import (
    claim_next_job,
    clear_all_jobs,
    create_job,
    get_all_jobs,
    get_stats,
    update_job_status,
)
from shared.logger import get_logger
from shared.models import JobResponse, JobStatusUpdate, WorkerHeartbeat, StatsResponse, JobStatus

logger = get_logger("controller")

app = FastAPI(title="RenderAgent Controller", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

workers_state: dict = {}


@app.get("/api/jobs/next")
def get_next_job(worker_id: str = Query(...)):
    try:
        job = claim_next_job(worker_id)
        if job is None:
            from fastapi.responses import Response

            return Response(status_code=204)
        resp = JobResponse.model_validate(job)
        return resp.model_dump(mode="json")
    except Exception as e:
        logger.error(f"Error in /jobs/next: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/{job_id}/status")
def set_job_status(job_id: str, body: JobStatusUpdate):
    try:
        job = update_job_status(
            job_id,
            status=body.status,
            output_path=body.output_path,
            error_message=body.error_message,
        )
        if job is None:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        resp = JobResponse.model_validate(job)
        return resp.model_dump(mode="json")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /jobs/{{id}}/status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workers/heartbeat")
def worker_heartbeat(body: WorkerHeartbeat):
    try:
        workers_state[body.worker_id] = {
            "worker_id": body.worker_id,
            "ip": body.ip,
            "last_seen": datetime.utcnow(),
            "jobs_completed": body.jobs_completed,
            "current_job_id": body.current_job_id,
            "utilization": body.utilization,
            "temperature": body.temperature,
            "fan_speed": body.fan_speed,
        }
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error in /workers/heartbeat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workers")
def list_workers():
    try:
        stale_cutoff = datetime.utcnow() - timedelta(hours=24)
        result = []
        for w_id, w in list(workers_state.items()):
            if w["last_seen"] < stale_cutoff:
                del workers_state[w_id]
                continue
            result.append(
                {
                    "worker_id": w["worker_id"],
                    "ip": w["ip"],
                    "last_seen": w["last_seen"].isoformat(),
                    "jobs_completed": w["jobs_completed"],
                    "current_job_id": w["current_job_id"],
                    "utilization": w.get("utilization"),
                    "temperature": w.get("temperature"),
                    "fan_speed": w.get("fan_speed"),
                }
            )
        return result
    except Exception as e:
        logger.error(f"Error in /workers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
def dashboard_stats():
    try:
        stats = get_stats()
        cutoff = datetime.utcnow() - timedelta(seconds=30)
        active_count = sum(1 for w in workers_state.values() if w["last_seen"] >= cutoff)
        return StatsResponse(
            queue_depth=stats["queue_depth"],
            done_today=stats["done_today"],
            failed_today=stats["failed_today"],
            active_workers=active_count,
        ).model_dump()
    except Exception as e:
        logger.error(f"Error in /stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/logs")
def recent_logs():
    try:
        logs_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"
        )
        log_path = os.path.join(logs_dir, "render-agent.log")
        if not os.path.exists(log_path):
            return {"lines": []}
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return {"lines": [line.rstrip("\n") for line in lines[-100:]]}
    except Exception as e:
        logger.error(f"Error in /logs: {e}")
        return {"lines": []}


@app.get("/api/jobs")
def list_jobs(status: str = Query(None)):
    try:
        jobs = get_all_jobs(status_filter=status)
        return [JobResponse.model_validate(j).model_dump(mode="json") for j in jobs]
    except Exception as e:
        logger.error(f"Error in /jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/jobs")
def delete_all_jobs():
    try:
        count = clear_all_jobs()
        return {"cleared": count}
    except Exception as e:
        logger.error(f"Error clearing jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


_dashboard_dir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "dashboard", "dist"
)
if os.path.isdir(_dashboard_dir):
    app.mount(
        "/",
        StaticFiles(directory=_dashboard_dir, html=True),
        name="dashboard",
    )