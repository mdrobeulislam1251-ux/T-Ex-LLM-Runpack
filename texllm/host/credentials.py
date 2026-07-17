"""
Auth profiles — same product model as NanoClaw / OpenClaw / AionUi:

  1) Subscription / session tokens (Claude setup-token, Codex OAuth, CLI login)
  2) Official API keys
  3) Local CLI spawn (agent keeps its own login)

Token sink lives on the host (.texllm/credentials.json). Secrets never returned
to the browser after save.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import stat
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel, Field


AuthMethod = Literal[
    "api_key",  # console API key
    "setup_token",  # Claude Max/Pro: paste output of `claude setup-token`
    "oauth_codex",  # ChatGPT / Codex subscription OAuth (PKCE)
    "oauth_google",  # Gemini / Google AI OAuth (PKCE) when client configured
    "local_cli",  # reuse claude/codex/gemini CLI already logged in on host
]
ProviderId = Literal["openai", "anthropic", "xai", "gemini", "mock", "custom"]


class AuthProfile(BaseModel):
    id: str
    provider: ProviderId = "custom"
    method: AuthMethod = "api_key"
    label: str = ""
    base_url: str = ""
    model: str = ""
    has_secret: bool = False
    agent_id: str = ""
    notes: str = ""
    # OAuth metadata (non-secret)
    account_hint: str = ""
    expires_at: Optional[float] = None


class AuthProfileCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    provider: ProviderId = "custom"
    method: AuthMethod = "api_key"
    label: str = ""
    base_url: str = ""
    model: str = ""
    # generic secret field: API key OR setup-token OR refresh material
    api_key: str = ""
    access_token: str = ""
    refresh_token: str = ""
    expires_at: Optional[float] = None
    agent_id: str = ""
    notes: str = ""
    account_hint: str = ""


class AuthStoreData(BaseModel):
    default_profile_id: Optional[str] = None
    profiles: List[AuthProfile] = Field(default_factory=list)
    # profile_id -> secret blob (string or JSON for OAuth packs)
    secrets: Dict[str, str] = Field(default_factory=dict)
    # ephemeral PKCE state
    oauth_pending: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


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
            pub.has_secret = bool(data.secrets.get(p.id))
            if not pub.label:
                pub.label = _default_label(p)
            profiles.append(pub.model_dump())
        return {
            "default_profile_id": data.default_profile_id,
            "profiles": profiles,
            "methods": {
                "setup_token": {
                    "providers": ["anthropic"],
                    "how": "Run `claude setup-token` (Claude Max/Pro), paste token. Same path NanoClaw/OpenClaw use for subscription auth.",
                },
                "oauth_codex": {
                    "providers": ["openai"],
                    "how": "PKCE login at auth.openai.com (ChatGPT/Codex subscription). Same family as OpenClaw `models auth login --provider openai`.",
                },
                "oauth_google": {
                    "providers": ["gemini"],
                    "how": "Google OAuth for Gemini/AI Studio when GOOGLE_OAUTH_CLIENT_ID is set.",
                },
                "local_cli": {
                    "providers": ["anthropic", "openai", "gemini"],
                    "how": "Like AionUi multi-agent mode: CLI already logged in (`claude auth login` / codex / gemini); T-ex spawns it.",
                },
                "api_key": {
                    "providers": ["openai", "anthropic", "xai", "gemini", "custom"],
                    "how": "Console API keys (pay-per-token).",
                },
            },
            "inspired_by": {
                "nanoclaw": "https://nanoclaw.dev / https://github.com/nanocoai/nanoclaw — Claude Agent SDK + setup-token or API key; OneCLI vault injects secrets; /add-codex for ChatGPT sub",
                "openclaw": "https://docs.openclaw.ai/concepts/oauth — Codex PKCE OAuth + Claude CLI reuse + setup-token sink",
                "aionui": "https://github.com/iOfficeAI/AionUi — API keys for built-in agent + auto-detect CLI agents that keep their own auth",
            },
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
            account_hint=body.account_hint,
            expires_at=body.expires_at,
        )

        secret_blob = _pack_secret(body)
        if secret_blob:
            data.secrets[profile.id] = secret_blob
        elif profile.id not in data.secrets:
            data.secrets[profile.id] = ""

        profile.has_secret = bool(data.secrets.get(profile.id))
        data.profiles = [p for p in data.profiles if p.id != profile.id]
        data.profiles.append(profile)
        if not data.default_profile_id:
            data.default_profile_id = profile.id
        self._save(data)
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

    def get_profile(self, profile_id: str) -> Optional[AuthProfile]:
        data = self._load()
        for p in data.profiles:
            if p.id == profile_id:
                return p
        return None

    def get_default(self) -> Optional[AuthProfile]:
        data = self._load()
        if not data.default_profile_id:
            return None
        return self.get_profile(data.default_profile_id)

    def get_secret_raw(self, profile_id: str) -> Optional[str]:
        return self._load().secrets.get(profile_id) or None

    def get_secret_pack(self, profile_id: str) -> Dict[str, Any]:
        raw = self.get_secret_raw(profile_id)
        if not raw:
            return {}
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
        return {"access_token": raw, "api_key": raw}

    def save_oauth_tokens(
        self,
        profile_id: str,
        *,
        access: str,
        refresh: str = "",
        expires_at: Optional[float] = None,
        account_hint: str = "",
        provider: ProviderId = "openai",
        method: AuthMethod = "oauth_codex",
        label: str = "",
    ) -> AuthProfile:
        body = AuthProfileCreate(
            id=profile_id,
            provider=provider,
            method=method,
            label=label or profile_id,
            access_token=access,
            refresh_token=refresh,
            expires_at=expires_at,
            account_hint=account_hint,
        )
        return self.upsert(body)

    def begin_oauth(self, provider: str, profile_id: str) -> Dict[str, Any]:
        """Start PKCE for Codex (OpenAI) or Google."""
        data = self._load()
        verifier = secrets.token_urlsafe(64)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )
        state = secrets.token_urlsafe(24)
        data.oauth_pending[state] = {
            "provider": provider,
            "profile_id": profile_id,
            "verifier": verifier,
            "created": time.time(),
        }
        self._save(data)

        if provider == "openai" or provider == "codex":
            client_id = os.environ.get("CODEX_OAUTH_CLIENT_ID", "")
            redirect = os.environ.get(
                "CODEX_OAUTH_REDIRECT_URI",
                f"http://127.0.0.1:{os.environ.get('HOST_PORT', '3006')}/v1/auth/oauth/codex/callback",
            )
            if not client_id:
                return {
                    "error": "Set CODEX_OAUTH_CLIENT_ID (OpenClaw-style Codex OAuth client).",
                    "state": state,
                    "hint": "Alternatively use method=api_key or local_cli (codex logged in).",
                }
            params = {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect,
                "scope": "openid profile email offline_access",
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
            url = "https://auth.openai.com/oauth/authorize?" + urlencode(params)
            return {
                "authorize_url": url,
                "state": state,
                "redirect_uri": redirect,
                "provider": "openai",
            }

        if provider == "google" or provider == "gemini":
            client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
            redirect = os.environ.get(
                "GOOGLE_OAUTH_REDIRECT_URI",
                f"http://127.0.0.1:{os.environ.get('HOST_PORT', '3006')}/v1/auth/oauth/google/callback",
            )
            if not client_id:
                return {
                    "error": "Set GOOGLE_OAUTH_CLIENT_ID for Gemini subscription/OAuth.",
                    "state": state,
                }
            params = {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect,
                "scope": "openid email https://www.googleapis.com/auth/cloud-platform",
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "access_type": "offline",
                "prompt": "consent",
            }
            url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
            return {
                "authorize_url": url,
                "state": state,
                "redirect_uri": redirect,
                "provider": "gemini",
            }

        return {"error": f"Unknown OAuth provider: {provider}"}

    def finish_oauth_codex(self, code: str, state: str) -> AuthProfile:
        data = self._load()
        pending = data.oauth_pending.pop(state, None)
        self._save(data)
        if not pending:
            raise ValueError("Unknown or expired OAuth state")
        client_id = os.environ.get("CODEX_OAUTH_CLIENT_ID", "")
        redirect = os.environ.get(
            "CODEX_OAUTH_REDIRECT_URI",
            f"http://127.0.0.1:{os.environ.get('HOST_PORT', '3006')}/v1/auth/oauth/codex/callback",
        )
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                "https://auth.openai.com/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect,
                    "client_id": client_id,
                    "code_verifier": pending["verifier"],
                },
            )
            resp.raise_for_status()
            tok = resp.json()
        access = tok.get("access_token") or ""
        refresh = tok.get("refresh_token") or ""
        expires_in = float(tok.get("expires_in") or 3600)
        return self.save_oauth_tokens(
            pending["profile_id"],
            access=access,
            refresh=refresh,
            expires_at=time.time() + expires_in,
            provider="openai",
            method="oauth_codex",
            label=pending.get("profile_id") or "chatgpt-codex",
            account_hint="chatgpt/codex",
        )

    def finish_oauth_google(self, code: str, state: str) -> AuthProfile:
        data = self._load()
        pending = data.oauth_pending.pop(state, None)
        self._save(data)
        if not pending:
            raise ValueError("Unknown or expired OAuth state")
        client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
        client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
        redirect = os.environ.get(
            "GOOGLE_OAUTH_REDIRECT_URI",
            f"http://127.0.0.1:{os.environ.get('HOST_PORT', '3006')}/v1/auth/oauth/google/callback",
        )
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code_verifier": pending["verifier"],
                },
            )
            resp.raise_for_status()
            tok = resp.json()
        access = tok.get("access_token") or ""
        refresh = tok.get("refresh_token") or ""
        expires_in = float(tok.get("expires_in") or 3600)
        return self.save_oauth_tokens(
            pending["profile_id"],
            access=access,
            refresh=refresh,
            expires_at=time.time() + expires_in,
            provider="gemini",
            method="oauth_google",
            label=pending.get("profile_id") or "gemini-oauth",
            account_hint="google",
        )


def _pack_secret(body: AuthProfileCreate) -> str:
    if body.access_token or body.refresh_token:
        return json.dumps(
            {
                "access_token": body.access_token or body.api_key,
                "refresh_token": body.refresh_token,
                "expires_at": body.expires_at,
            }
        )
    if body.api_key:
        # setup_token and api_key both store as opaque secret
        return body.api_key
    return ""


def _default_label(p: AuthProfile) -> str:
    if p.method == "setup_token":
        return "Claude Max/Pro setup-token"
    if p.method == "oauth_codex":
        return "ChatGPT / Codex OAuth"
    if p.method == "oauth_google":
        return "Gemini Google OAuth"
    if p.method == "local_cli":
        return f"Local CLI: {p.agent_id or p.provider}"
    return f"{p.provider} API key"


def probe_cli_auth(agent_id: str) -> Dict[str, Any]:
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
        "claude": [
            [agent.path, "auth", "status", "--text"],
            [agent.path, "auth", "status"],
        ],
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
            if any(
                x in low
                for x in ("logged in", "authenticated", "apikeysource", "account")
            ):
                logged_in = "not logged" not in low and "none" not in low
            if "401" in low:
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


def resolve_runtime() -> Dict[str, Any]:
    """
    Resolve default auth profile into something runners can use.
    Mirrors OpenClaw token sink / NanoClaw vault injection point.
    """
    store = credential_store
    profile = store.get_default()
    if not profile:
        # fall back to env LLM_*
        from texllm.config import get_settings

        s = get_settings()
        if s.llm_api_key:
            return {
                "source": "env",
                "method": "api_key",
                "provider": "openai",
                "base_url": s.llm_base_url,
                "api_key": s.llm_api_key,
                "model": s.llm_model,
                "use_local_cli": False,
            }
        return {
            "source": "mock",
            "method": "mock",
            "provider": "mock",
            "use_local_cli": False,
        }

    pack = store.get_secret_pack(profile.id)
    access = pack.get("access_token") or pack.get("api_key") or ""
    if profile.method == "local_cli":
        return {
            "source": "profile",
            "profile_id": profile.id,
            "method": "local_cli",
            "provider": profile.provider,
            "agent_id": profile.agent_id or "claude",
            "use_local_cli": True,
            "model": profile.model,
        }

    base = profile.base_url
    if not base:
        base = {
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com",
            "xai": "https://api.x.ai/v1",
            "gemini": "https://generativelanguage.googleapis.com/v1beta",
        }.get(profile.provider, "https://api.openai.com/v1")

    return {
        "source": "profile",
        "profile_id": profile.id,
        "method": profile.method,
        "provider": profile.provider,
        "base_url": base,
        "api_key": access,
        "model": profile.model,
        "use_local_cli": False,
        "extra_headers": _extra_headers(profile.method, profile.provider),
    }


def _extra_headers(method: str, provider: str) -> Dict[str, str]:
    if provider == "anthropic" or method == "setup_token":
        return {
            "anthropic-version": "2023-06-01",
            # Agent-SDK / Claude Code style clients often set beta headers;
            # keep minimal so plain messages API can still work.
        }
    return {}


credential_store = CredentialStore()
