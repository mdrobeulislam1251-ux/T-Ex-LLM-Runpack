"""Export team brains (+ skills) to versioned firmware packages under firmware/."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from texllm.workspace.db import WorkspaceDB, get_workspace


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return s[:48] or "brain"


def export_team_firmware(
    team_slug: str,
    *,
    version: str = "0.1.0",
    firmware_root: Optional[Path] = None,
    db: Optional[WorkspaceDB] = None,
) -> Dict[str, Any]:
    """
    Write firmware/<team-slug>-agents@version/ with:
      - manifest.yaml (planner/executor/reviewer/integrator + team brains as roles)
      - prompts/*.md from each brain
      - skills.md catalog from team skills
    """
    db = db or get_workspace()
    team = db.get_team(team_slug)
    if not team:
        raise KeyError(f"Unknown team: {team_slug}")

    brains = db.list_brains(team["id"])
    skills = db.list_skills(team["id"])
    root = Path(firmware_root or "firmware")
    pkg_id = f"{team['slug']}-agents"
    pkg_dir = root / pkg_id
    prompts_dir = pkg_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    # Core runner roles (required by TeamRunner)
    core_roles = [
        ("planner", "cheap", 0.2, _planner_prompt(team, brains)),
        ("executor", "default", 0.3, _executor_prompt(team, brains, skills)),
        ("reviewer", "cheap", 0.0, _reviewer_prompt(team)),
        ("integrator", "cheap", 0.1, _integrator_prompt(team)),
    ]
    roles_manifest: List[Dict[str, Any]] = []
    for role_name, tier, temp, body in core_roles:
        fname = f"{role_name}.md"
        (prompts_dir / fname).write_text(body, encoding="utf-8")
        roles_manifest.append(
            {
                "name": role_name,
                "model_tier": tier,
                "tools": ["echo", "now", "word_count", "checklist"]
                if role_name == "executor"
                else [],
                "prompt_file": f"prompts/{fname}",
                "temperature": temp,
            }
        )

    # Export each brain as an additional specialist prompt file
    brain_files = []
    for b in brains:
        slug = _slugify(b["name"])
        fname = f"brain-{slug}.md"
        content = (
            f"# {b['name']}\n\n"
            f"Role: {b.get('role') or 'specialist'}\n"
            f"Team: {team['name']} (`{team['slug']}`)\n\n"
            f"{b.get('prompt') or 'Specialist agent for this team.'}\n"
        )
        (prompts_dir / fname).write_text(content, encoding="utf-8")
        brain_files.append({"name": b["name"], "role": b.get("role"), "file": fname})

    skills_md = ["# Team skills\n"]
    for s in skills:
        skills_md.append(f"## {s['name']}\n\n{s.get('description') or ''}\n\n")
        if s.get("body"):
            skills_md.append(f"{s['body']}\n\n")
    (pkg_dir / "skills.md").write_text("".join(skills_md), encoding="utf-8")

    manifest = {
        "id": pkg_id,
        "version": version,
        "name": f"{team['name']} Agents",
        "description": (
            f"Auto-exported from T-ex workspace team `{team['slug']}`. "
            f"{team.get('description') or ''}"
        ).strip(),
        "default_tools": ["echo", "now", "word_count", "checklist"],
        "limits": {
            "max_iterations": 10,
            "max_review_retries": 2,
            "max_cost_usd": 1.0,
        },
        "roles": roles_manifest,
        "tex_export": {
            "team_slug": team["slug"],
            "team_id": team["id"],
            "brains": brain_files,
            "skill_count": len(skills),
        },
    }
    (pkg_dir / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    (pkg_dir / "README.md").write_text(
        f"# {manifest['name']} (`{pkg_id}@{version}`)\n\n"
        f"Exported from workspace team **{team['name']}**.\n\n"
        f"## Run\n\n"
        f"```bash\n"
        f'python3 -m texllm.cli run "Your goal" --firmware {pkg_id} --version {version}\n'
        f"# or after setting default in host jobs\n"
        f"```\n\n"
        f"Brains: {len(brains)} · Skills: {len(skills)}\n",
        encoding="utf-8",
    )

    db.log_activity(
        team["id"],
        "firmware_export",
        f"Exported firmware {pkg_id}@{version}",
        str(pkg_dir),
    )

    return {
        "package_id": pkg_id,
        "version": version,
        "path": str(pkg_dir),
        "brains_exported": len(brains),
        "skills_exported": len(skills),
        "manifest": manifest,
    }


def _planner_prompt(team: Dict[str, Any], brains: List[Dict[str, Any]]) -> str:
    names = ", ".join(b["name"] for b in brains) or "Lead"
    return f"""# Planner — {team['name']}

You plan work for the **{team['name']}** team (`{team['slug']}`).
Focus: {team.get('description') or 'team delivery'}
Available specialist brains: {names}

Return JSON only:
{{"plan": ["step"], "success_criteria": ["criterion"], "notes": ""}}
"""


def _executor_prompt(
    team: Dict[str, Any], brains: List[Dict[str, Any]], skills: List[Dict[str, Any]]
) -> str:
    brain_block = "\n".join(
        f"- **{b['name']}** ({b.get('role')}): {(b.get('prompt') or '')[:300]}"
        for b in brains
    )
    skill_block = "\n".join(
        f"- **{s['name']}**: {s.get('description') or ''}" for s in skills
    )
    return f"""# Executor — {team['name']}

You execute for **{team['name']}** (`{team['slug']}`).
Focus: {team.get('description') or ''}

## Brains (embody these specialists as needed)
{brain_block or '- Lead specialist'}

## Skills
{skill_block or '- none registered'}

Write a complete draft answer in markdown.
"""


def _reviewer_prompt(team: Dict[str, Any]) -> str:
    return f"""# Reviewer — {team['name']}

Verify the draft meets success criteria for **{team['name']}**.
Return JSON only:
{{"passed": true, "feedback": "", "score": 0.0}}
"""


def _integrator_prompt(team: Dict[str, Any]) -> str:
    return f"""# Integrator — {team['name']}

Package approved work for the **{team['name']}** dashboard API.
Return JSON only:
{{"summary": "", "output": {{"answer": "", "team": "{team['slug']}"}}}}
"""
