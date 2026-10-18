"""Host API — jobs, local CLI agents, firmware, static web UI."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from texllm import __version__
from texllm.agents.detect import detect_report
from texllm.agents.local_cli import LocalCliError, run_local_agent
from texllm.config import Settings, get_settings
from texllm.firmware.loader import list_firmware
from texllm.host.aliases import AgentAliases, alias_store
from texllm.host.credentials import (
    AuthProfileCreate,
    credential_store,
    probe_cli_auth,
    resolve_runtime,
)
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
    use_aliases: bool = Field(
        default=True,
        description="Prepend agent/user name aliases to the prompt",
    )


# ----- Auth profiles (API keys + local CLI sessions) -----


@app.get("/v1/auth/profiles")
def auth_profiles_list(_: None = Depends(require_api_key)) -> dict:
    """List auth profiles (secrets redacted). See docs/AUTH.md."""
    return credential_store.list_public()


@app.put("/v1/auth/profiles")
def auth_profiles_upsert(
    body: AuthProfileCreate,
    _: None = Depends(require_api_key),
) -> dict:
    """Create or update a profile. api_key is stored only on the host disk."""
    # Grok defaults
    if body.provider in ("xai", "grok") and not body.base_url:
        body.base_url = "https://api.x.ai/v1"
    if body.provider in ("xai", "grok") and not body.model:
        body.model = "grok-3"
    if body.provider == "grok":
        body.provider = "xai"
    profile = credential_store.upsert(body)
    # Always make the profile just saved the default when it has a key
    if body.api_key or body.method == "local_cli":
        try:
            credential_store.set_default(profile.id)
        except Exception:  # noqa: BLE001
            pass
    from texllm.providers import describe_active_provider

    return {
        **profile.model_dump(),
        "active_ai": describe_active_provider(),
    }


@app.post("/v1/auth/profiles/{profile_id}/default")
def auth_profiles_default(
    profile_id: str,
    _: None = Depends(require_api_key),
) -> dict:
    try:
        credential_store.set_default(profile_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Profile not found") from exc
    return {"default_profile_id": profile_id}


@app.delete("/v1/auth/profiles/{profile_id}")
def auth_profiles_delete(
    profile_id: str,
    _: None = Depends(require_api_key),
) -> dict:
    credential_store.delete(profile_id)
    return {"ok": True}


@app.get("/v1/auth/cli-status/{agent_id}")
def auth_cli_status(
    agent_id: str,
    _: None = Depends(require_api_key),
) -> dict:
    """Probe whether a local CLI appears logged in (does not return tokens)."""
    return probe_cli_auth(agent_id)


@app.get("/v1/auth/runtime")
def auth_runtime(_: None = Depends(require_api_key)) -> dict:
    """Resolved default profile (secret redacted) — vault injection point."""
    rt = resolve_runtime()
    safe = {k: v for k, v in rt.items() if k != "api_key"}
    if rt.get("api_key"):
        safe["has_secret"] = True
        safe["secret_preview"] = str(rt["api_key"])[:6] + "…"
    return safe


class OAuthStartBody(BaseModel):
    provider: str = Field(..., description="openai|codex|google|gemini")
    profile_id: str = Field(default="default-oauth")


@app.post("/v1/auth/oauth/start")
def auth_oauth_start(
    body: OAuthStartBody,
    _: None = Depends(require_api_key),
) -> dict:
    """Start PKCE OAuth (Codex ChatGPT or Google Gemini) — OpenClaw-style."""
    return credential_store.begin_oauth(body.provider, body.profile_id)


@app.get("/v1/auth/oauth/codex/callback")
def auth_oauth_codex_callback(code: str = "", state: str = "") -> dict:
    if not code or not state:
        raise HTTPException(status_code=400, detail="code and state required")
    try:
        profile = credential_store.finish_oauth_codex(code, state)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    credential_store.set_default(profile.id)
    return {
        "ok": True,
        "profile": profile.model_dump(),
        "message": "ChatGPT/Codex OAuth saved. Set as default profile.",
    }


@app.get("/v1/auth/oauth/google/callback")
def auth_oauth_google_callback(code: str = "", state: str = "") -> dict:
    if not code or not state:
        raise HTTPException(status_code=400, detail="code and state required")
    try:
        profile = credential_store.finish_oauth_google(code, state)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    credential_store.set_default(profile.id)
    return {
        "ok": True,
        "profile": profile.model_dump(),
        "message": "Google/Gemini OAuth saved.",
    }


class SetupTokenBody(BaseModel):
    """Paste Claude Max/Pro token from `claude setup-token` (NanoClaw path)."""

    profile_id: str = "claude-max"
    token: str = Field(..., min_length=10)
    model: str = "claude-sonnet-4-20250514"
    label: str = "Claude Max/Pro setup-token"
    set_default: bool = True


@app.post("/v1/auth/claude/setup-token")
def auth_claude_setup_token(
    body: SetupTokenBody,
    _: None = Depends(require_api_key),
) -> dict:
    profile = credential_store.upsert(
        AuthProfileCreate(
            id=body.profile_id,
            provider="anthropic",
            method="setup_token",
            label=body.label,
            model=body.model,
            api_key=body.token.strip(),
            notes="From `claude setup-token` — NanoClaw/OpenClaw subscription path",
        )
    )
    if body.set_default:
        credential_store.set_default(profile.id)
    return {"ok": True, "profile": profile.model_dump()}


class ClaudeCliSessionBody(BaseModel):
    profile_id: str = "claude-cli"
    set_default: bool = True


@app.post("/v1/auth/claude/use-cli")
def auth_claude_use_cli(
    body: ClaudeCliSessionBody = ClaudeCliSessionBody(),
    _: None = Depends(require_api_key),
) -> dict:
    """Set default profile to local Claude Code session (`claude auth login`)."""
    profile = credential_store.upsert(
        AuthProfileCreate(
            id=body.profile_id,
            provider="anthropic",
            method="local_cli",
            agent_id="claude",
            label="Claude Code CLI session",
            notes="Uses host `claude` login — no API key",
        )
    )
    if body.set_default:
        credential_store.set_default(profile.id)
    status = probe_cli_auth("claude")
    return {"ok": True, "profile": profile.model_dump(), "cli_status": status}


class ChatBody(BaseModel):
    message: str = Field(..., min_length=1)
    use_aliases: bool = True


@app.post("/v1/chat")
def chat(
    body: ChatBody,
    settings: Settings = Depends(_settings),
    _: None = Depends(require_api_key),
) -> dict:
    """
    Claude-first chat — uses default auth profile
    (setup-token → claude CLI, local_cli, or Anthropic API key).
    """
    from texllm.providers import get_provider
    from texllm.providers.base import ChatMessage

    aliases = alias_store.get()
    system = (
        f"You are {aliases.agent_name}, a helpful agent for T-ex LLM. "
        f"Address the user as {aliases.user_name}. Be clear and concise."
    )
    if body.use_aliases:
        system = aliases.prompt_preamble() + "\n" + system

    try:
        provider = get_provider(settings)
        result = provider.complete(
            [
                ChatMessage(role="system", content=system),
                ChatMessage(role="user", content=body.message),
            ],
            temperature=0.3,
            max_tokens=2048,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    rt = resolve_runtime()
    return {
        "role": "assistant",
        "content": result.content,
        "model": result.model,
        "provider": result.provider,
        "auth_method": rt.get("method"),
        "agent_name": aliases.agent_name,
        "user_name": aliases.user_name,
    }


# ----- Multi-team workspace (shared SQLite: web + CLI) -----


@app.get("/v1/workspace")
def workspace_overview(_: None = Depends(require_api_key)) -> dict:
    from texllm.workspace import get_workspace

    return get_workspace().overview()


@app.get("/v1/workspace/teams")
def workspace_teams(_: None = Depends(require_api_key)) -> dict:
    from texllm.workspace import get_workspace

    return {"teams": get_workspace().list_teams()}


@app.post("/v1/workspace/teams")
def workspace_create_team(
    body: Dict[str, Any],
    _: None = Depends(require_api_key),
) -> dict:
    from texllm.workspace import get_workspace

    slug = str(body.get("slug") or "").strip().lower().replace(" ", "-")
    name = str(body.get("name") or "").strip()
    if not slug or not name:
        raise HTTPException(status_code=400, detail="slug and name required")
    try:
        team = get_workspace().create_team(
            slug=slug,
            name=name,
            kind=str(body.get("kind") or "custom"),
            description=str(body.get("description") or ""),
            color=str(body.get("color") or "#64748b"),
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return team


@app.get("/v1/workspace/teams/{slug}")
def workspace_team_dashboard(
    slug: str,
    _: None = Depends(require_api_key),
) -> dict:
    from texllm.workspace import get_workspace

    try:
        return get_workspace().dashboard(slug)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Team not found") from exc


@app.post("/v1/workspace/teams/{slug}/run")
def workspace_team_run(
    slug: str,
    body: Dict[str, Any],
    _: None = Depends(require_api_key),
) -> dict:
    from texllm.workspace.team_run import run_team_flow

    goal = str(body.get("goal") or "").strip()
    if not goal:
        raise HTTPException(status_code=400, detail="goal required")
    mode = str(body.get("mode") or "chat").strip() or "chat"
    workdir = str(body.get("workdir") or "").strip() or None
    verify = str(body.get("verify") or "").strip() or None
    try:
        return run_team_flow(slug, goal, mode=mode, workdir=workdir, verify=verify)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Team not found") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/v1/workspace/teams/{slug}/run-async")
def workspace_team_run_async(
    slug: str,
    body: Dict[str, Any],
    _: None = Depends(require_api_key),
) -> dict:
    """Queue a team run and return immediately — poll /v1/jobs/{job_id}.

    This is the dispatch surface for UIs (Command Deck) that need a job id
    right away instead of holding a request open for the whole run.
    """
    from texllm.host.dispatch import dispatch_team_job

    goal = str(body.get("goal") or "").strip()
    if not goal:
        raise HTTPException(status_code=400, detail="goal required")
    mode = str(body.get("mode") or "chat").strip() or "chat"
    workdir = str(body.get("workdir") or "").strip() or None
    verify = str(body.get("verify") or "").strip() or None
    try:
        team, job = dispatch_team_job(
            slug, goal, store=store, mode=mode, workdir=workdir, verify=verify
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Team not found") from exc
    return {
        "job_id": job.id,
        "team": team["slug"],
        "status": job.status.value,
        "mode": job.mode,
    }


@app.post("/v1/workspace/domain-review")
def workspace_domain_review(
    body: Dict[str, Any],
    _: None = Depends(require_api_key),
) -> dict:
    """Review a domain/website → ideas, brains, skills in shared DB."""
    from texllm.workspace.domain_review import review_domain

    domain = str(body.get("domain") or body.get("url") or "").strip()
    if not domain:
        raise HTTPException(status_code=400, detail="domain or url required")
    try:
        return review_domain(domain, notes=str(body.get("notes") or ""))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/v1/workspace/ideas")
def workspace_ideas(_: None = Depends(require_api_key)) -> dict:
    from texllm.workspace import get_workspace

    return {"ideas": get_workspace().list_ideas()}


@app.post("/v1/workspace/brains")
def workspace_add_brain(
    body: Dict[str, Any],
    _: None = Depends(require_api_key),
) -> dict:
    from texllm.workspace import get_workspace

    ws = get_workspace()
    team = ws.get_team(str(body.get("team_slug") or body.get("team_id") or ""))
    if not team:
        raise HTTPException(status_code=400, detail="team_slug required")
    return ws.add_brain(
        team["id"],
        name=str(body.get("name") or "Brain"),
        role=str(body.get("role") or "specialist"),
        prompt=str(body.get("prompt") or ""),
        model_tier=str(body.get("model_tier") or "default"),
    )


@app.post("/v1/workspace/skills")
def workspace_add_skill(
    body: Dict[str, Any],
    _: None = Depends(require_api_key),
) -> dict:
    from texllm.workspace import get_workspace

    ws = get_workspace()
    team_id = None
    if body.get("team_slug"):
        team = ws.get_team(str(body["team_slug"]))
        team_id = team["id"] if team else None
    return ws.add_skill(
        name=str(body.get("name") or "Skill"),
        description=str(body.get("description") or ""),
        body=str(body.get("body") or ""),
        path=str(body.get("path") or ""),
        team_id=team_id,
    )


@app.post("/v1/workspace/personal-bd/run")
def workspace_personal_bd(
    body: Dict[str, Any],
    _: None = Depends(require_api_key),
) -> dict:
    from texllm.workspace.team_run import run_personal_bd

    goal = str(body.get("goal") or "").strip()
    if not goal:
        raise HTTPException(status_code=400, detail="goal required")
    try:
        return run_personal_bd(goal)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.patch("/v1/workspace/kpis/{kpi_id}")
def workspace_update_kpi(
    kpi_id: str,
    body: Dict[str, Any],
    _: None = Depends(require_api_key),
) -> dict:
    from texllm.workspace import get_workspace

    try:
        return get_workspace().update_kpi(
            kpi_id,
            value=body.get("value"),
            trend=body.get("trend"),
            target=body.get("target"),
            label=body.get("label"),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="KPI not found") from exc


@app.post("/v1/workspace/teams/{slug}/kanban")
def workspace_add_card(
    slug: str,
    body: Dict[str, Any],
    _: None = Depends(require_api_key),
) -> dict:
    from texllm.workspace import get_workspace

    ws = get_workspace()
    team = ws.get_team(slug)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    title = str(body.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title required")
    return ws.add_kanban_card(
        team["id"],
        title,
        detail=str(body.get("detail") or ""),
        column_key=str(body.get("column_key") or "backlog"),
        priority=str(body.get("priority") or "med"),
        assignee=str(body.get("assignee") or "agent"),
    )


@app.post("/v1/workspace/kanban/{card_id}/move")
def workspace_move_card(
    card_id: str,
    body: Dict[str, Any],
    _: None = Depends(require_api_key),
) -> dict:
    from texllm.workspace import get_workspace

    col = str(body.get("column_key") or "").strip()
    if not col:
        raise HTTPException(status_code=400, detail="column_key required")
    try:
        return get_workspace().move_kanban_card(card_id, col)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Card not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/workspace/teams/{slug}/export-firmware")
def workspace_export_firmware(
    slug: str,
    body: Dict[str, Any] = None,
    _: None = Depends(require_api_key),
) -> dict:
    """Export team brains/skills to firmware/<slug>-agents/ for TeamRunner."""
    from texllm.workspace.export_firmware import export_team_firmware

    body = body or {}
    version = str(body.get("version") or "0.1.0")
    try:
        return export_team_firmware(slug, version=version)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Team not found") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ----- Company Runbook Agent (product spine: intent → deploy) -----


@app.get("/v1/runbook")
def runbook_get(_: None = Depends(require_api_key)) -> dict:
    """Pre-loaded company runbook phases + progress + provider list."""
    from texllm.runbook.state import get_runbook

    snap = get_runbook().snapshot()
    # attach auth profile summary (no secrets)
    auth = credential_store.list_public()
    snap["auth_profiles"] = auth.get("profiles") or []
    snap["auth_default"] = auth.get("default_profile_id")
    from texllm.providers import describe_active_provider

    snap["active_ai"] = describe_active_provider()
    return snap


@app.patch("/v1/runbook/phases/{phase_id}")
def runbook_patch_phase(
    phase_id: str,
    body: Dict[str, Any],
    _: None = Depends(require_api_key),
) -> dict:
    from texllm.runbook.state import get_runbook

    try:
        return get_runbook().update_phase(
            phase_id,
            status=body.get("status"),
            placeholder=body.get("placeholder"),
            result=body.get("result"),
            company_name=body.get("company_name"),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown phase") from exc


@app.post("/v1/runbook/phases/{phase_id}/run")
def runbook_run_phase(
    phase_id: str,
    body: Dict[str, Any] = None,
    settings: Settings = Depends(_settings),
    _: None = Depends(require_api_key),
) -> dict:
    """
    Execute a runbook phase. Always returns updated snapshot.
    Uses connected provider; mock fills placeholders so UI always updates.
    """
    from texllm.runbook.state import get_runbook, json_safe
    from texllm.providers import get_provider
    from texllm.providers.base import ChatMessage
    from texllm.host.credentials import resolve_runtime

    body = body or {}
    rb = get_runbook()
    snap = rb.snapshot()
    phase = next((p for p in snap["phases"] if p["id"] == phase_id), None)
    if not phase:
        raise HTTPException(status_code=404, detail="Unknown phase")

    rb.update_phase(phase_id, status="running")
    rb.log(f"Phase started: {phase['title']}", phase_id)
    notes = str(body.get("notes") or "")
    company = str(
        body.get("company_name") or snap.get("company_name") or "Your Company"
    ).strip() or "Your Company"

    try:
        # Domain with URL → workspace domain review (may call LLM)
        if phase_id == "domain" and body.get("domain"):
            from texllm.workspace.domain_review import review_domain

            result = json_safe(
                review_domain(str(body["domain"]), notes=notes)
            )
            filled = _fill_phase_placeholders(phase, company, notes, result)
            rb.update_phase(
                phase_id,
                status="done",
                placeholder=filled,
                result={
                    "summary": result.get("overview")
                    or f"Domain review complete for {body.get('domain')}",
                    "content": json.dumps(result, indent=2, default=str)[:4000],
                    "mode": "domain_review",
                    "provider": result.get("provider") or "unknown",
                },
                company_name=company,
            )
            rb.log(f"Phase done: {phase['title']}", "domain_review")
            return rb.snapshot()

        # Fast path: single LLM completion (works with mock / API / Claude CLI)
        rt = resolve_runtime()
        provider = get_provider(settings)
        goal = (
            f"You are the {phase.get('agent_role')} for company runbook phase "
            f"[{phase['title']}].\n"
            f"Company name: {company}\n"
            f"Current placeholders (JSON): {json.dumps(phase.get('placeholder') or {})}\n"
            f"Notes: {notes or 'none'}\n"
            f"Required outputs: {phase.get('outputs')}\n\n"
            "Write a concrete markdown draft that FILLS the placeholders with "
            "realistic content (not brackets). Be specific and useful."
        )
        completion = provider.complete(
            [
                ChatMessage(
                    role="system",
                    content=(
                        "You fill company runbook phases for T-ex. "
                        "Return clear markdown. No empty placeholders."
                    ),
                ),
                ChatMessage(role="user", content=goal),
            ],
            max_tokens=1800,
            temperature=0.4,
        )

        content = (completion.content or "").strip()
        # CLI auth failures or empty output are failures — never substitute a
        # fabricated draft and call the phase done.
        bad = (
            not content
            or "not logged in" in content.lower()
            or "please run /login" in content.lower()
            or content.lower().startswith("error")
        )
        if bad:
            raise RuntimeError(
                "provider returned unusable output for this phase: "
                f"{(completion.content or '(empty)')[:200]}"
            )

        filled = _fill_phase_placeholders(phase, company, notes, {"content": content})
        result = {
            "summary": content[:280].replace("\n", " "),
            "content": content,
            "mode": "phase_run",
            "provider": completion.provider,
            "auth_method": rt.get("method") or settings.resolve_provider(),
            "model": completion.model,
        }
        rb.update_phase(
            phase_id,
            status="done",
            placeholder=filled,
            result=result,
            company_name=company,
        )
        rb.log(
            f"Phase done: {phase['title']}",
            f"provider={completion.provider} method={result['auth_method']}",
        )
        return rb.snapshot()
    except Exception as exc:  # noqa: BLE001
        logger.exception("runbook phase %s failed", phase_id)
        # Honest failure: the phase is FAILED with the real error. No demo
        # placeholders, no fabricated draft — the UI shows what actually broke
        # and the phase can be re-run once a provider is connected.
        try:
            from texllm.providers import describe_active_provider

            ai = describe_active_provider()
        except Exception:  # noqa: BLE001
            ai = {}
        rb.update_phase(
            phase_id,
            status="failed",
            result={
                "summary": f"Phase failed: {str(exc)[:160]}",
                "error": str(exc),
                "mode": "error",
                "provider": ai.get("name"),
                "auth_method": ai.get("method"),
                "hint": ai.get("hint"),
            },
            company_name=company,
        )
        rb.log(f"Phase failed: {phase['title']}", str(exc)[:200])
        return rb.snapshot()


def _fill_phase_placeholders(
    phase: Dict[str, Any],
    company: str,
    notes: str,
    extra: Dict[str, Any],
) -> Dict[str, Any]:
    """Replace [bracket] placeholders with demo company values so UI updates."""
    ph = dict(phase.get("placeholder") or {})
    replacements = {
        "company_name": company,
        "one_liner": f"{company} — agentic company runbook to product deployment",
        "problem": "Fragmented tools and no single spine from idea to deploy",
        "audience": "Founders and ops teams shipping multi-agent products",
        "success_metric": "Time from intent to production deploy (days)",
        "domain": str(extra.get("domain") or ph.get("domain") or "example.com")
        .replace("[", "")
        .replace("]", ""),
        "positioning": f"{company} owns the company-to-deploy agent spine",
        "brains_per_team": "Lead + planner/executor/reviewer per team",
        "skills": "Domain review, firmware export, GTM sequences",
        "eval_suite": "Golden tasks per phase",
        "ci": "pytest + web build green",
        "pricing": "Starter / Pro / Enterprise (placeholder)",
        "onboarding": "Day-0: connect provider → run Intent → Domain",
        "host": "0.0.0.0:3006",
        "auth": "API keys or Claude CLI / setup-token",
        "access": "localhost | tailnet | domain",
        "health": "/health green",
    }
    out: Dict[str, Any] = {}
    for k, v in ph.items():
        if isinstance(v, str) and v.startswith("["):
            out[k] = replacements.get(k, v.strip("[]") or company)
        elif isinstance(v, list):
            out[k] = [
                x.strip("[]") if isinstance(x, str) and x.startswith("[") else x
                for x in v
            ]
            if k == "competitors" and all(
                isinstance(x, str) and "Competitor" in x for x in (v or [])
            ):
                out[k] = ["Incumbent SaaS", "Horizontal AI chat", "Homegrown scripts"]
            if k == "mvp_features" and any(
                isinstance(x, str) and x.startswith("[") for x in (v or [])
            ):
                out[k] = [
                    "Company runbook Intent→Deploy",
                    "Multi-team agents",
                    "Provider connect (Claude/GPT/Gemini/Grok)",
                ]
            if k == "packages":
                out[k] = ["sample-assistant@0.1.0", "sales-agents@0.1.0"]
            if k == "channels":
                out[k] = ["Web console", "tex CLI", "@T-ex in Claude Code"]
        else:
            out[k] = v
    if notes:
        out["notes"] = notes
    return out


@app.get("/v1/settings/aliases", response_model=AgentAliases)
def get_aliases(_: None = Depends(require_api_key)) -> AgentAliases:
    """Names: what the user calls the agent, and what the agent calls the user."""
    return alias_store.get()


@app.put("/v1/settings/aliases", response_model=AgentAliases)
def put_aliases(
    body: AgentAliases,
    _: None = Depends(require_api_key),
) -> AgentAliases:
    """Save agent ↔ user addressing aliases."""
    return alias_store.set(body)


@app.patch("/v1/settings/aliases", response_model=AgentAliases)
def patch_aliases(
    body: Dict[str, Any],
    _: None = Depends(require_api_key),
) -> AgentAliases:
    """Partial update of aliases."""
    allowed = {"agent_name", "user_name", "agent_aliases", "user_aliases"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid alias fields")
    return alias_store.patch(updates)


# ----- Messaging channels (docs/CHANNELS.md) -----
# Webhook routes are deliberately OUTSIDE require_api_key: chat platforms
# cannot send custom headers, so each adapter authenticates with its
# platform's own mechanism (signature / secret token / JWT) over the raw body.


def _channel_response(resp: "object") -> Response:
    from texllm.channels.base import WebhookResponse

    assert isinstance(resp, WebhookResponse)
    if resp.text is not None:
        return PlainTextResponse(resp.text, status_code=resp.status_code)
    return JSONResponse(resp.json_body or {"ok": True}, status_code=resp.status_code)


def _channel_request(raw: bytes, request: Request, method: str) -> "object":
    from texllm.channels.base import WebhookRequest

    return WebhookRequest(
        body=raw,
        headers={k.lower(): v for k, v in request.headers.items()},
        query=dict(request.query_params),
        method=method,
    )


@app.get("/v1/channels")
def channels_status(_: None = Depends(require_api_key)) -> dict:
    """Adapter status: configured channels, allowlist counts, flags.
    Counts and names only — never secret values."""
    from texllm.channels.service import get_channel_service

    return get_channel_service().status_report()


@app.get("/v1/channels/{channel}/webhook")
async def channel_webhook_get(channel: str, request: Request) -> Response:
    from texllm.channels.service import get_channel_service

    wreq = _channel_request(b"", request, "GET")
    resp = await run_in_threadpool(get_channel_service().handle_get, channel, wreq)
    return _channel_response(resp)


@app.post("/v1/channels/{channel}/webhook")
async def channel_webhook_post(channel: str, request: Request) -> Response:
    from texllm.channels.service import get_channel_service

    raw = await request.body()  # exact wire bytes — HMAC verification needs them
    wreq = _channel_request(raw, request, "POST")
    # threadpool: adapter sends are blocking httpx calls (bounded ~10s timeouts)
    resp = await run_in_threadpool(get_channel_service().handle_post, channel, wreq)
    return _channel_response(resp)


@app.get("/health")
def health(settings: Settings = Depends(_settings)) -> dict:
    from texllm.providers import describe_active_provider

    active = describe_active_provider()
    return {
        "status": "ok",
        "version": __version__,
        "port": settings.host_port,
        "serve_web": settings.serve_web,
        "allow_local_cli": settings.allow_local_cli,
        "llm_provider": active.get("name") or settings.resolve_provider(),
        "ai": active,
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
            "agent_aliases": True,
        },
        "aliases": alias_store.get().model_dump(),
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
    prompt = body.prompt
    if body.use_aliases:
        aliases = alias_store.get()
        prompt = f"{aliases.prompt_preamble()}\n\n{body.prompt}"
    try:
        result = run_local_agent(
            body.agent_id,
            prompt,
            cwd=str(settings.local_cli_cwd),
            timeout_sec=body.timeout_sec or settings.local_cli_timeout_sec,
        )
    except LocalCliError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result["aliases_applied"] = body.use_aliases
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
        mode=(body.mode or "chat"),
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
    # Opt-in convenience: run the Telegram long-poll worker inside `serve`.
    # Only when no webhook secret is set — Telegram forbids webhook + getUpdates
    # together. Lives here (not a FastAPI startup hook) so TestClient never
    # spawns it.
    if (
        settings.telegram_poll_on_serve
        and settings.telegram_bot_token.strip()
        and not settings.telegram_webhook_secret.strip()
    ):
        from texllm.channels.service import get_channel_service
        from texllm.channels.telegram_poll import start_poller_thread

        start_poller_thread(get_channel_service())
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
