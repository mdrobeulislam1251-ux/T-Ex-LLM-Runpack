"""Run a team agentic flow via host TeamRunner + workspace context."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from texllm.config import get_settings
from texllm.schemas import Job
from texllm.workers.runner import TeamRunner
from texllm.workspace.db import WorkspaceDB, get_workspace


def prepare_team_job(
    team_slug: str,
    goal: str,
    *,
    db: Optional[WorkspaceDB] = None,
    mode: str = "chat",
    workdir: Optional[str] = None,
) -> tuple[Dict[str, Any], Job]:
    """Resolve team context + firmware and build the Job (without running it).

    Shared by the synchronous flow (CLI, /run) and the async dispatch endpoint
    (/run-async) so both queue identical jobs.
    """
    db = db or get_workspace()
    team = db.get_team(team_slug)
    if not team:
        raise KeyError(f"Unknown team: {team_slug}")

    brains = db.list_brains(team["id"])
    skills = db.list_skills(team["id"])
    brain_ctx = "\n".join(
        f"- {b['name']} ({b['role']}): {(b.get('prompt') or '')[:200]}" for b in brains
    )
    skill_ctx = "\n".join(
        f"- {s['name']}: {s.get('description') or ''}" for s in skills
    )

    full_goal = (
        f"[T-ex team={team['slug']} name={team['name']}]\n"
        f"Team focus: {team.get('description')}\n"
        f"Brains:\n{brain_ctx or '(default)'}\n"
        f"Skills:\n{skill_ctx or '(none)'}\n\n"
        f"User goal: {goal}"
    )

    settings = get_settings()
    # Prefer auto-exported team firmware if present
    fw_id = "sample-assistant"
    fw_ver = "0.1.0"
    pkg = Path(settings.firmware_dir) / f"{team['slug']}-agents"
    if not (pkg / "manifest.yaml").is_file():
        # Fresh workspace (a user project dir): sample-assistant only ships inside
        # the runtime checkout, so generate this team's firmware from its seeded
        # brains/skills instead of failing the very first run.
        try:
            from texllm.workspace.export_firmware import export_team_firmware

            export_team_firmware(
                team["slug"], firmware_root=Path(settings.firmware_dir), db=db
            )
        except Exception:  # noqa: BLE001 — fall through to sample-assistant
            pass
    if (pkg / "manifest.yaml").is_file():
        fw_id = f"{team['slug']}-agents"
        try:
            import yaml

            man = yaml.safe_load((pkg / "manifest.yaml").read_text(encoding="utf-8")) or {}
            fw_ver = str(man.get("version") or "0.1.0")
        except Exception:  # noqa: BLE001
            fw_ver = "0.1.0"

    job_input: Dict[str, Any] = {"goal": goal, "team": team["slug"]}
    if workdir:
        job_input["workdir"] = workdir
    job = Job(
        firmware_id=fw_id,
        firmware_version=fw_ver,
        goal=full_goal,
        input=job_input,
        mode=(mode or "chat"),
    )
    return team, job


def run_team_flow(
    team_slug: str,
    goal: str,
    *,
    db: Optional[WorkspaceDB] = None,
    mode: str = "chat",
    workdir: Optional[str] = None,
) -> Dict[str, Any]:
    db = db or get_workspace()
    team, job = prepare_team_job(
        team_slug, goal, db=db, mode=mode, workdir=workdir
    )
    job = TeamRunner(settings=get_settings()).run_job(job)

    db.log_activity(
        team["id"],
        "flow_run",
        f"Flow: {goal[:80]}",
        f"status={job.status.value} mode={job.mode}",
    )

    return {
        "team": team,
        "job_id": job.id,
        "status": job.status.value,
        "error": job.error,
        "result": job.result.model_dump() if job.result else None,
    }


def run_personal_bd(goal: str, *, db: Optional[WorkspaceDB] = None) -> Dict[str, Any]:
    return run_team_flow("personal-bd", goal, db=db)
