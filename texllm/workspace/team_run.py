"""Run a team agentic flow via host TeamRunner + workspace context."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from texllm.config import get_settings
from texllm.schemas import Job
from texllm.workers.runner import TeamRunner
from texllm.workspace.db import WorkspaceDB, get_workspace


def run_team_flow(
    team_slug: str,
    goal: str,
    *,
    db: Optional[WorkspaceDB] = None,
) -> Dict[str, Any]:
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
    if (pkg / "manifest.yaml").is_file():
        fw_id = f"{team['slug']}-agents"
        try:
            import yaml

            man = yaml.safe_load((pkg / "manifest.yaml").read_text(encoding="utf-8")) or {}
            fw_ver = str(man.get("version") or "0.1.0")
        except Exception:  # noqa: BLE001
            fw_ver = "0.1.0"

    job = Job(
        firmware_id=fw_id,
        firmware_version=fw_ver,
        goal=full_goal,
        input={"goal": goal, "team": team["slug"]},
    )
    job = TeamRunner(settings=settings).run_job(job)

    db.log_activity(
        team["id"],
        "flow_run",
        f"Flow: {goal[:80]}",
        f"status={job.status.value}",
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
