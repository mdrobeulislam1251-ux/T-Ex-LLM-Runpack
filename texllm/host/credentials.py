"""Auth profiles: API keys + local CLI session bindings (not browser OAuth scraping)."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


AuthMethod = Literal["api_key", "local_cli", "oauth_google"]
ProviderId = Literal["openai", "anthropic", "xai", "gemini", "mock", "custom"]


class AuthProfile(BaseModel):
    id: str
    provider: ProviderId = "custom"
    method: AuthMethod = "api_key"
    label: str = ""
    # For api_key / custom HTTP
    base_url: str = ""
    model: str = ""
    # Secret never returned in full after save
    has_api_key: bool = False
    # For local_cli
    agent_id: str = ""
    # Status only
    notes: str = ""


class AuthProfileCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    provider: ProviderId = "custom"
    method: AuthMethod = "api_key"
    label: str = ""
    base_url: str = ""
    model: str = ""
    api_key: str = ""
    agent_id: str = ""
    notes: str = ""


class AuthStoreData(BaseModel):
    default_profile_id: Optional[str] = None
    profiles: List[AuthProfile] = Field(default_factory=list)
    # secrets keyed by profile id — never expose via public JSON as-is
    secrets: Dict[str, str] = Field(default_factory=dict)


class CredentialStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or Path(".texllm") / "credentials.json"
        self._lock = threading.Lock()
        self._data: Optional[AuthStoreData] = None

    def _load(self) -> AuthStoreData:
        if self._data is not None:
            return self._data
        if self.path.is_file():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                self._data = AuthStoreData.model_validate(raw)
                return self._data
            except (OSError, json.JSONDecodeError, ValueError):
                pass
        self._data = AuthStoreData()
        return self._data

    def _save(self, data: AuthStoreData) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(data.model_dump_json(indent=2), encoding="utf-8")
        try:
            os.chmod(self.path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
        self._data = data

    def list_public(self) -> Dict[str, Any]:
        data = self._load()
        profiles = []
        for p in data.profiles:
            pub = p.model_copy()
            pub.has_api_key = bool(data.secrets.get(p.id))
            if p.method == "api_key" and not pub.label:
                pub.label = f"{p.provider} API key"
            if p.method == "local_cli" and not pub.label:
                pub.label = f"Local CLI: {p.agent_id or p.provider}"
            profiles.append(pub.model_dump())
        return {
            "default_profile_id": data.default_profile_id,
            "profiles": profiles,
            "methods_explained": {
                "api_key": "Official HTTP API key (OpenAI, Anthropic, xAI, Gemini, etc.)",
                "local_cli": "Reuse Claude Code / Codex / Gemini CLI login on this host (OpenClaw-style session)",
                "oauth_google": "Google OAuth / Vertex (configure GCP client — not browser cookie scrape)",
            },
            "honest_notes": [
                "T-ex does not implement Claude.ai / ChatGPT browser session hijacking.",
                "Anthropic consumer OAuth is intended for Claude products; third-party subscription OAuth is restricted — use API keys or local Claude CLI.",
                "Local CLI sessions never send your CLI token to the browser; the host spawns the CLI process.",
            ],
        }

    def upsert(self, body: AuthProfileCreate) -> AuthProfile:
        data = self._load()
        profile = AuthProfile(
            id=body.id.strip(),
            provider=body.provider,
            method=body.method,
            label=body.label or body.id,
            base_url=body.base_url,
            model=body.model,
            agent_id=body.agent_id,
            notes=body.notes,
            has_api_key=bool(body.api_key),
        )
        data.profiles = [p for p in data.profiles if p.id != profile.id]
        data.profiles.append(profile)
        if body.api_key:
            data.secrets[profile.id] = body.api_key
        elif profile.id not in data.secrets:
            data.secrets[profile.id] = ""
        if not data.default_profile_id:
            data.default_profile_id = profile.id
        self._save(data)
        profile.has_api_key = bool(data.secrets.get(profile.id))
        return profile

    def set_default(self, profile_id: str) -> None:
        data = self._load()
        if not any(p.id == profile_id for p in data.profiles):
            raise KeyError(profile_id)
        data.default_profile_id = profile_id
        self._save(data)

    def delete(self, profile_id: str) -> None:
        data = self._load()
        data.profiles = [p for p in data.profiles if p.id != profile_id]
        data.secrets.pop(profile_id, None)
        if data.default_profile_id == profile_id:
            data.default_profile_id = data.profiles[0].id if data.profiles else None
        self._save(data)

    def get_secret(self, profile_id: str) -> Optional[str]:
        data = self._load()
        return data.secrets.get(profile_id) or None

    def get_default(self) -> Optional[AuthProfile]:
        data = self._load()
        if not data.default_profile_id:
            return None
        for p in data.profiles:
            if p.id == data.default_profile_id:
                return p
        return None


def probe_cli_auth(agent_id: str) -> Dict[str, Any]:
    """Best-effort CLI session status (no token extraction)."""
    from texllm.agents.detect import detect_agents

    agents = {a.id: a for a in detect_agents()}
    agent = agents.get(agent_id)
    if not agent:
        return {
            "agent_id": agent_id,
            "installed": False,
            "logged_in": None,
            "detail": "CLI not found on PATH",
        }

    argv_options = {
        "claude": [[agent.path, "auth", "status", "--text"], [agent.path, "auth", "status"]],
        "codex": [[agent.path, "login", "status"], [agent.path, "--version"]],
        "gemini": [[agent.path, "auth", "status"], [agent.path, "--version"]],
    }
    options = argv_options.get(agent_id, [[agent.path, "--version"]])
    last_out = ""
    for argv in options:
        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
            last_out = ((proc.stdout or "") + (proc.stderr or "")).strip()[:2000]
            low = last_out.lower()
            logged_in = None
            if "logged in" in low or "authenticated" in low or "apiKeySource" in last_out:
                logged_in = "none" not in low and "not logged" not in low
            if "error" in low and "401" in low:
                logged_in = False
            return {
                "agent_id": agent_id,
                "installed": True,
                "path": agent.path,
                "version": agent.version,
                "logged_in": logged_in,
                "detail": last_out[:500] or f"exit {proc.returncode}",
                "method": "local_cli_session",
            }
        except (OSError, subprocess.TimeoutExpired) as exc:
            last_out = str(exc)
            continue
    return {
        "agent_id": agent_id,
        "installed": True,
        "path": agent.path,
        "logged_in": None,
        "detail": last_out or "Could not probe auth",
        "method": "local_cli_session",
    }


credential_store = CredentialStore()
