"""Host API — create/poll jobs, list firmware, health."""

from __future__ import annotations

import logging
import threading
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse

from texllm import __version__
from texllm.config import Settings, get_settings
from texllm.firmware.loader import list_firmware
from texllm.schemas import Job, JobCreate, JobStatus, utcnow
from texllm.host.store import JobStore
from texllm.workers.runner import TeamRunner

logger = logging.getLogger(__name__)

store = JobStore()
app = FastAPI(
    title="T-ex LLM Host",
    version=__version__,
    description="Multi-agent host for team runners and agentic firmware",
)


def _settings() -> Settings:
    return get_settings()


def require_api_key(
    x_api_key: Optional[str] = Header(default=None),
    settings: Settings = Depends(_settings),
) -> None:
    expected = settings.host_api_key
    if expected and expected != "change-me":
        if x_api_key != expected:
            raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")
    # Dev default "change-me" accepts missing key for local demos


def _run_async(job_id: str) -> None:
    job = store.get(job_id)
    if not job:
        return
    runner = TeamRunner()
    updated = runner.run_job(job)
    store.put(updated)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/v1/firmware")
def firmware_list(
    settings: Settings = Depends(_settings),
    _: None = Depends(require_api_key),
) -> dict:
    return {"firmware": list_firmware(settings.firmware_dir)}


@app.post("/v1/jobs", response_model=Job)
def create_job(
    body: JobCreate,
    settings: Settings = Depends(_settings),
    _: None = Depends(require_api_key),
) -> Job:
    goal = body.goal or str(body.input.get("goal") or body.input.get("prompt") or "")
    if not goal:
        raise HTTPException(status_code=400, detail="goal or input.goal required")

    job = Job(
        firmware_id=body.firmware_id,
        firmware_version=body.firmware_version,
        goal=goal,
        input=body.input,
        status=JobStatus.queued,
    )
    store.put(job)

    # Background worker thread (MVP — replace with real queue later)
    t = threading.Thread(target=_run_async, args=(job.id,), daemon=True)
    t.start()
    return job


@app.get("/v1/jobs/{job_id}", response_model=Job)
def get_job(
    job_id: str,
    _: None = Depends(require_api_key),
) -> Job:
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/v1/jobs")
def list_jobs(
    limit: int = 50,
    _: None = Depends(require_api_key),
) -> dict:
    return {"jobs": store.list(limit=limit)}


@app.post("/v1/jobs/{job_id}/cancel", response_model=Job)
def cancel_job(
    job_id: str,
    _: None = Depends(require_api_key),
) -> Job:
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in (JobStatus.succeeded, JobStatus.failed, JobStatus.cancelled):
        return job
    # Best-effort for MVP in-flight jobs
    if job.status == JobStatus.queued:
        job.status = JobStatus.cancelled
        job.finished_at = utcnow()
        job.touch()
        store.put(job)
    return job


@app.exception_handler(Exception)
async def unhandled(request, exc):  # type: ignore[no-untyped-def]
    logger.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"detail": str(exc)})


def main() -> None:
    import uvicorn

    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())
    uvicorn.run(
        "texllm.host.app:app",
        host="0.0.0.0",
        port=settings.host_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
