"""Host API — jobs, local CLI agents, firmware, static web UI."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from texllm import __version__
from texllm.agents.detect import detect_report
from texllm.agents.local_cli import LocalCliError, run_local_agent
from texllm.config import Settings, get_settings
from texllm.firmware.loader import list_firmware
from texllm.host.store import JobStore
from texllm.schemas import Job, JobCreate, JobStatus, utcnow
from texllm.workers.runner import TeamRunner

logger = logging.getLogger(__name__)

store = JobStore()
app = FastAPI(
    title="T-ex LLM",
    version=__version__,
    description=(
        "Multi-agent host: team runners, OpenAI-compatible providers, "
        "and local terminal agent CLI spawn (PATH auto-detect)."
    ),
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


def _run_async(job_id: str) -> None:
    job = store.get(job_id)
    if not job:
        return
    runner = TeamRunner()
    updated = runner.run_job(job)
    store.put(updated)


class LocalAgentRunRequest(BaseModel):
    agent_id: str = Field(..., description="Detected agent id, e.g. claude, codex")
    prompt: str = Field(..., min_length=1)
    timeout_sec: Optional[int] = None


@app.get("/health")
def health(settings: Settings = Depends(_settings)) -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "port": settings.host_port,
        "serve_web": settings.serve_web,
        "allow_local_cli": settings.allow_local_cli,
        "llm_provider": settings.resolve_provider(),
    }


@app.get("/v1/system")
def system_info(settings: Settings = Depends(_settings)) -> dict:
    """Honest capability report for operators and the web UI."""
    report = detect_report()
    return {
        "version": __version__,
        "capabilities": {
            "team_runner": True,
            "openai_compat_api": True,
            "mock_provider": True,
            "local_cli_detect": True,
            "local_cli_spawn": settings.allow_local_cli,
            "web_ui": settings.serve_web,
        },
        "honest_notes": [
            "Local CLI mode uses tools already installed and authenticated on this machine (e.g. `claude auth login`). T-ex does not replace those logins with LLM_API_KEY.",
            "Not every detected CLI supports non-interactive spawn; the API reports noninteractive=true when a known prompt path exists.",
            "Team runners use mock or OpenAI-compatible HTTP APIs, independent of terminal CLIs.",
            "This is not a full interactive TUI multiplexer; for interactive sessions open Claude/Codex/etc. in your own terminal against this repo.",
        ],
        "agents": report,
        "bind": f"{settings.host_bind}:{settings.host_port}",
    }


@app.get("/v1/agents")
def list_agents(
    _: None = Depends(require_api_key),
) -> dict:
    """Scan PATH (+ common install dirs) for terminal AI CLIs."""
    return detect_report()


@app.post("/v1/agents/run")
def run_agent(
    body: LocalAgentRunRequest,
    settings: Settings = Depends(_settings),
    _: None = Depends(require_api_key),
) -> Dict[str, Any]:
    """Spawn a detected local agent CLI in a backend subprocess."""
    if not settings.allow_local_cli:
        raise HTTPException(
            status_code=403,
            detail="Local CLI spawn disabled (ALLOW_LOCAL_CLI=false)",
        )
    try:
        result = run_local_agent(
            body.agent_id,
            body.prompt,
            cwd=str(settings.local_cli_cwd),
            timeout_sec=body.timeout_sec or settings.local_cli_timeout_sec,
        )
    except LocalCliError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


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


def _mount_web(settings: Settings) -> None:
    if not settings.serve_web:
        return
    dist = Path(settings.web_dist_dir)
    if not dist.is_absolute():
        dist = Path.cwd() / dist
    if not dist.is_dir() or not (dist / "index.html").exists():
        logger.warning(
            "Web UI dist not found at %s — run: cd apps/web && npm run build",
            dist,
        )
        return

    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    @app.get("/")
    def spa_index() -> FileResponse:
        return FileResponse(dist / "index.html")

    # SPA fallback for client routes (must be last registered patterns)
    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith("v1/") or full_path in ("health", "docs", "openapi.json", "redoc"):
            raise HTTPException(status_code=404)
        candidate = dist / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(dist / "index.html")


def main() -> None:
    import uvicorn

    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())
    _mount_web(settings)
    logger.info(
        "T-ex LLM listening on %s:%s (web=%s, local_cli=%s)",
        settings.host_bind,
        settings.host_port,
        settings.serve_web,
        settings.allow_local_cli,
    )
    uvicorn.run(
        app,
        host=settings.host_bind,
        port=settings.host_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
