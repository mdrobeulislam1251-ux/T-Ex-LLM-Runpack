"""CredentialStore unit tests: persistence, redaction, OAuth, runtime resolution."""

from __future__ import annotations

import json
import stat
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from texllm.agents.detect import DetectedAgent
from texllm.host import credentials as cred_mod
from texllm.host.credentials import (
    AuthProfile,
    AuthProfileCreate,
    CredentialStore,
    _default_label,
    _pack_secret,
    probe_cli_auth,
)


def make_store(tmp_path: Path) -> CredentialStore:
    return CredentialStore(path=tmp_path / "creds.json")


# ----- load / save -----


def test_load_missing_file_is_empty(tmp_path: Path):
    store = make_store(tmp_path)
    data = store.list_public()
    assert data["profiles"] == []
    assert data["default_profile_id"] is None


def test_load_corrupt_file_is_empty(tmp_path: Path):
    path = tmp_path / "creds.json"
    path.write_text("{not json", encoding="utf-8")
    store = CredentialStore(path=path)
    assert store.list_public()["profiles"] == []


def test_upsert_persists_with_owner_only_mode(tmp_path: Path):
    store = make_store(tmp_path)
    store.upsert(AuthProfileCreate(id="k1", provider="openai", api_key="sk-abc123"))
    assert store.path.is_file()
    assert stat.S_IMODE(store.path.stat().st_mode) == (stat.S_IRUSR | stat.S_IWUSR)

    # A fresh store at the same path reads the saved state back
    reread = CredentialStore(path=store.path)
    profile = reread.get_profile("k1")
    assert profile is not None
    assert profile.provider == "openai"
    assert reread.get_secret_raw("k1") == "sk-abc123"
    assert reread.get_default() is not None
    assert reread.get_default().id == "k1"


def test_list_public_never_contains_secret(tmp_path: Path):
    store = make_store(tmp_path)
    store.upsert(
        AuthProfileCreate(id="k1", provider="anthropic", api_key="sk-ant-topsecret")
    )
    public = store.list_public()
    assert public["profiles"][0]["has_secret"] is True
    assert "sk-ant-topsecret" not in json.dumps(public)


# ----- upsert semantics -----


def test_first_profile_becomes_default(tmp_path: Path):
    store = make_store(tmp_path)
    store.upsert(AuthProfileCreate(id="first", api_key="sk-1"))
    store.upsert(AuthProfileCreate(id="second", api_key="sk-2"))
    assert store.get_default().id == "first"


def test_upsert_same_id_replaces_not_duplicates(tmp_path: Path):
    store = make_store(tmp_path)
    store.upsert(AuthProfileCreate(id="k1", provider="openai", api_key="sk-old"))
    store.upsert(AuthProfileCreate(id="k1", provider="xai", api_key="sk-new"))
    profiles = store.list_public()["profiles"]
    assert [p["id"] for p in profiles] == ["k1"]
    assert profiles[0]["provider"] == "xai"
    assert store.get_secret_raw("k1") == "sk-new"


def test_upsert_metadata_only_keeps_existing_secret(tmp_path: Path):
    store = make_store(tmp_path)
    store.upsert(AuthProfileCreate(id="k1", api_key="sk-keep"))
    store.upsert(AuthProfileCreate(id="k1", label="renamed"))
    assert store.get_secret_raw("k1") == "sk-keep"
    assert store.get_profile("k1").label == "renamed"
    assert store.get_profile("k1").has_secret is True


def test_set_default_unknown_raises(tmp_path: Path):
    store = make_store(tmp_path)
    with pytest.raises(KeyError):
        store.set_default("ghost")


def test_delete_reassigns_default_and_drops_secret(tmp_path: Path):
    store = make_store(tmp_path)
    store.upsert(AuthProfileCreate(id="a", api_key="sk-a"))
    store.upsert(AuthProfileCreate(id="b", api_key="sk-b"))
    store.delete("a")
    assert store.get_default().id == "b"
    assert store.get_secret_raw("a") is None
    store.delete("b")
    assert store.get_default() is None


# ----- secret packing -----


def test_pack_secret_variants():
    oauth = _pack_secret(
        AuthProfileCreate(id="x", access_token="at", refresh_token="rt", expires_at=9.0)
    )
    assert json.loads(oauth) == {
        "access_token": "at",
        "refresh_token": "rt",
        "expires_at": 9.0,
    }
    assert _pack_secret(AuthProfileCreate(id="x", api_key="sk-1")) == "sk-1"
    assert _pack_secret(AuthProfileCreate(id="x")) == ""


def test_get_secret_pack_shapes(tmp_path: Path):
    store = make_store(tmp_path)
    store.upsert(AuthProfileCreate(id="plain", api_key="sk-raw"))
    store.upsert(AuthProfileCreate(id="oauth", access_token="at-1", refresh_token="rt-1"))
    assert store.get_secret_pack("plain") == {
        "access_token": "sk-raw",
        "api_key": "sk-raw",
    }
    pack = store.get_secret_pack("oauth")
    assert pack["access_token"] == "at-1"
    assert pack["refresh_token"] == "rt-1"
    assert store.get_secret_pack("missing") == {}


def test_default_label_per_method():
    assert "setup-token" in _default_label(AuthProfile(id="x", method="setup_token"))
    assert "Codex" in _default_label(AuthProfile(id="x", method="oauth_codex"))
    assert "Gemini" in _default_label(AuthProfile(id="x", method="oauth_google"))
    assert "Local CLI: claude" in _default_label(
        AuthProfile(id="x", method="local_cli", agent_id="claude")
    )
    assert "openai API key" in _default_label(AuthProfile(id="x", provider="openai"))


# ----- OAuth (PKCE) -----


def test_begin_oauth_unknown_provider(tmp_path: Path):
    store = make_store(tmp_path)
    out = store.begin_oauth("aol", "p1")
    assert "Unknown OAuth provider" in out["error"]


def test_begin_oauth_codex_without_client_id(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("CODEX_OAUTH_CLIENT_ID", raising=False)
    store = make_store(tmp_path)
    out = store.begin_oauth("codex", "p1")
    assert "CODEX_OAUTH_CLIENT_ID" in out["error"]
    assert out["state"]


def test_begin_oauth_codex_builds_authorize_url(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CODEX_OAUTH_CLIENT_ID", "client-123")
    store = make_store(tmp_path)
    out = store.begin_oauth("openai", "p1")
    url = out["authorize_url"]
    assert url.startswith("https://auth.openai.com/oauth/authorize?")
    assert "client-123" in url
    assert "code_challenge=" in url
    assert out["state"] in url
    # PKCE verifier is persisted for the callback
    pending = store._load().oauth_pending[out["state"]]
    assert pending["profile_id"] == "p1"
    assert pending["verifier"]


def test_begin_oauth_google_builds_authorize_url(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "gclient-9")
    store = make_store(tmp_path)
    out = store.begin_oauth("gemini", "p2")
    assert out["authorize_url"].startswith(
        "https://accounts.google.com/o/oauth2/v2/auth?"
    )
    assert out["provider"] == "gemini"


def test_finish_oauth_unknown_state_raises(tmp_path: Path):
    store = make_store(tmp_path)
    with pytest.raises(ValueError):
        store.finish_oauth_codex("code", "bogus-state")


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeHttpxClient:
    payload = {"access_token": "at-xyz", "refresh_token": "rt-xyz", "expires_in": 1200}
    last_post = {}

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def post(self, url, data=None):
        type(self).last_post = {"url": url, "data": data or {}}
        return _FakeResponse(self.payload)


def test_finish_oauth_codex_saves_tokens(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CODEX_OAUTH_CLIENT_ID", "client-123")
    monkeypatch.setattr(cred_mod.httpx, "Client", _FakeHttpxClient)
    store = make_store(tmp_path)
    started = store.begin_oauth("codex", "my-codex")

    profile = store.finish_oauth_codex("auth-code-1", started["state"])
    assert profile.id == "my-codex"
    assert profile.provider == "openai"
    assert profile.method == "oauth_codex"
    assert profile.expires_at is not None
    assert profile.expires_at > time.time()
    pack = store.get_secret_pack("my-codex")
    assert pack["access_token"] == "at-xyz"
    assert pack["refresh_token"] == "rt-xyz"
    # Token exchange sent the PKCE verifier, and the state is single-use
    assert _FakeHttpxClient.last_post["data"]["code_verifier"]
    assert started["state"] not in store._load().oauth_pending
    with pytest.raises(ValueError):
        store.finish_oauth_codex("auth-code-1", started["state"])


# ----- resolve_runtime fallback chain -----


@pytest.fixture
def runtime_store(tmp_path: Path, monkeypatch):
    """Fresh store bound as the module singleton, with a clean settings env."""
    monkeypatch.chdir(tmp_path)  # keep Settings from reading the repo's .env
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    from texllm import config as config_mod

    config_mod.get_settings.cache_clear()
    store = make_store(tmp_path)
    monkeypatch.setattr(cred_mod, "credential_store", store)
    yield store
    config_mod.get_settings.cache_clear()


def test_resolve_runtime_mock_when_nothing_configured(runtime_store):
    rt = cred_mod.resolve_runtime()
    assert rt["source"] == "mock"
    assert rt["method"] == "mock"
    assert rt["use_local_cli"] is False


def test_resolve_runtime_env_key_fallback(runtime_store, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-env-key")
    from texllm import config as config_mod

    config_mod.get_settings.cache_clear()
    rt = cred_mod.resolve_runtime()
    assert rt["source"] == "env"
    assert rt["method"] == "api_key"
    assert rt["api_key"] == "sk-env-key"


def test_resolve_runtime_api_key_profile_with_provider_defaults(runtime_store):
    runtime_store.upsert(
        AuthProfileCreate(id="claude-key", provider="anthropic", api_key="sk-ant-1")
    )
    rt = cred_mod.resolve_runtime()
    assert rt["source"] == "profile"
    assert rt["profile_id"] == "claude-key"
    assert rt["base_url"] == "https://api.anthropic.com"
    assert rt["api_key"] == "sk-ant-1"
    assert rt["extra_headers"]["anthropic-version"]


def test_resolve_runtime_xai_default_model(runtime_store):
    runtime_store.upsert(AuthProfileCreate(id="grok", provider="xai", api_key="xai-1"))
    rt = cred_mod.resolve_runtime()
    assert rt["base_url"] == "https://api.x.ai/v1"
    assert rt["model"] == "grok-3"


def test_resolve_runtime_prefers_api_key_over_keyless_local_cli(runtime_store):
    # Broken-but-default local_cli profile (no secret), plus a real API key profile
    runtime_store.upsert(
        AuthProfileCreate(id="cli", method="local_cli", agent_id="claude")
    )
    runtime_store.upsert(
        AuthProfileCreate(id="backup", provider="openai", api_key="sk-backup")
    )
    assert runtime_store.get_default().id == "cli"
    rt = cred_mod.resolve_runtime()
    assert rt["profile_id"] == "backup"
    assert rt["method"] == "api_key"


def test_resolve_runtime_local_cli_with_secret_stays_local(runtime_store):
    runtime_store.upsert(
        AuthProfileCreate(
            id="cli", method="local_cli", agent_id="claude", api_key="sk-session"
        )
    )
    rt = cred_mod.resolve_runtime()
    assert rt["use_local_cli"] is True
    assert rt["agent_id"] == "claude"
    assert rt["method"] == "local_cli"


# ----- probe_cli_auth -----


def _fake_detect(*ids):
    return lambda: [
        DetectedAgent(id=i, binary=i, path=f"/usr/bin/{i}", version="1.0") for i in ids
    ]


def _fake_run(stdout: str = "", stderr: str = "", returncode: int = 0):
    def run(argv, **kwargs):
        return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)

    return run


def test_probe_cli_not_installed(monkeypatch):
    from texllm.agents import detect as detect_mod

    monkeypatch.setattr(detect_mod, "detect_agents", _fake_detect())
    out = probe_cli_auth("claude")
    assert out["installed"] is False
    assert out["logged_in"] is None


def test_probe_cli_logged_in(monkeypatch):
    from texllm.agents import detect as detect_mod

    monkeypatch.setattr(detect_mod, "detect_agents", _fake_detect("claude"))
    monkeypatch.setattr(
        cred_mod.subprocess, "run", _fake_run("Logged in as dev@example.com (Account: acme)")
    )
    out = probe_cli_auth("claude")
    assert out["installed"] is True
    assert out["logged_in"] is True
    assert out["version"] == "1.0"


def test_probe_cli_not_logged_in(monkeypatch):
    from texllm.agents import detect as detect_mod

    monkeypatch.setattr(detect_mod, "detect_agents", _fake_detect("claude"))
    monkeypatch.setattr(cred_mod.subprocess, "run", _fake_run("Not logged in"))
    out = probe_cli_auth("claude")
    assert out["logged_in"] is False


def test_probe_cli_401_means_logged_out(monkeypatch):
    from texllm.agents import detect as detect_mod

    monkeypatch.setattr(detect_mod, "detect_agents", _fake_detect("claude"))
    monkeypatch.setattr(cred_mod.subprocess, "run", _fake_run("HTTP 401 unauthorized"))
    out = probe_cli_auth("claude")
    assert out["logged_in"] is False


def test_probe_cli_all_probes_fail(monkeypatch):
    from texllm.agents import detect as detect_mod

    monkeypatch.setattr(detect_mod, "detect_agents", _fake_detect("claude"))

    def boom(argv, **kwargs):
        raise OSError("spawn failed")

    monkeypatch.setattr(cred_mod.subprocess, "run", boom)
    out = probe_cli_auth("claude")
    assert out["installed"] is True
    assert out["logged_in"] is None
    assert "spawn failed" in out["detail"]
