"""Host auth API tests: profiles, runtime resolution, OAuth, setup-token, chat."""

from __future__ import annotations

import os

os.environ["LLM_PROVIDER"] = "mock"
os.environ["HOST_API_KEY"] = "test-key"

H = {"X-API-Key": "test-key"}


def test_auth_endpoints_require_api_key(host_client):
    # Valid bodies where required, so a 422 can never mask the missing key
    for method, path, body in [
        ("GET", "/v1/auth/profiles", None),
        ("PUT", "/v1/auth/profiles", {"id": "x"}),
        ("POST", "/v1/auth/profiles/x/default", None),
        ("DELETE", "/v1/auth/profiles/x", None),
        ("GET", "/v1/auth/runtime", None),
        ("POST", "/v1/auth/oauth/start", {"provider": "codex"}),
        ("POST", "/v1/auth/claude/setup-token", {"token": "sk-ant-oat01-xyz"}),
        ("POST", "/v1/chat", {"message": "hi"}),
    ]:
        r = host_client.request(method, path, json=body)
        assert r.status_code == 401, f"{method} {path} -> {r.status_code}"


def test_profile_upsert_fills_xai_defaults_and_redacts(host_client):
    # NOTE: provider "grok" is rejected by the AuthProfileCreate Literal with a
    # 422 — the in-handler grok→xai normalization is unreachable. Clients must
    # send "xai"; the handler then fills the Grok base_url/model defaults.
    assert (
        host_client.put(
            "/v1/auth/profiles",
            headers=H,
            json={"id": "g", "provider": "grok", "api_key": "k"},
        ).status_code
        == 422
    )

    r = host_client.put(
        "/v1/auth/profiles",
        headers=H,
        json={"id": "grok-main", "provider": "xai", "api_key": "xai-supersecret-123"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "xai"
    assert body["base_url"] == "https://api.x.ai/v1"
    assert body["model"] == "grok-3"
    assert body["has_secret"] is True
    assert "xai-supersecret-123" not in r.text

    listing = host_client.get("/v1/auth/profiles", headers=H)
    assert listing.status_code == 200
    data = listing.json()
    assert [p["id"] for p in data["profiles"]] == ["grok-main"]
    # Saving a profile with a key makes it the default
    assert data["default_profile_id"] == "grok-main"
    assert "xai-supersecret-123" not in listing.text


def test_set_default_and_delete_profile(host_client):
    for pid in ("one", "two"):
        host_client.put(
            "/v1/auth/profiles",
            headers=H,
            json={"id": pid, "provider": "openai", "api_key": f"sk-{pid}"},
        )

    assert (
        host_client.post("/v1/auth/profiles/ghost/default", headers=H).status_code
        == 404
    )
    r = host_client.post("/v1/auth/profiles/one/default", headers=H)
    assert r.status_code == 200
    assert r.json()["default_profile_id"] == "one"

    assert host_client.delete("/v1/auth/profiles/one", headers=H).json()["ok"] is True
    data = host_client.get("/v1/auth/profiles", headers=H).json()
    assert [p["id"] for p in data["profiles"]] == ["two"]
    # Default falls back to the remaining profile
    assert data["default_profile_id"] == "two"


def test_auth_runtime_redacts_secret(host_client):
    host_client.put(
        "/v1/auth/profiles",
        headers=H,
        json={"id": "claude-key", "provider": "anthropic", "api_key": "sk-ant-verysecret"},
    )
    r = host_client.get("/v1/auth/runtime", headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body["method"] == "api_key"
    assert body["provider"] == "anthropic"
    assert body["has_secret"] is True
    assert body["secret_preview"] == "sk-ant…"
    assert "api_key" not in body
    assert "verysecret" not in r.text


def test_auth_runtime_mock_when_unconfigured(host_client):
    r = host_client.get("/v1/auth/runtime", headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body["method"] == "mock"
    assert "secret_preview" not in body


def test_oauth_start_without_client_id_returns_hint(host_client, monkeypatch):
    monkeypatch.delenv("CODEX_OAUTH_CLIENT_ID", raising=False)
    r = host_client.post(
        "/v1/auth/oauth/start", headers=H, json={"provider": "codex"}
    )
    assert r.status_code == 200
    body = r.json()
    assert "CODEX_OAUTH_CLIENT_ID" in body["error"]
    assert body["state"]


def test_oauth_start_codex_builds_authorize_url(host_client, monkeypatch):
    monkeypatch.setenv("CODEX_OAUTH_CLIENT_ID", "client-123")
    r = host_client.post(
        "/v1/auth/oauth/start",
        headers=H,
        json={"provider": "openai", "profile_id": "codex-sub"},
    )
    body = r.json()
    assert body["provider"] == "openai"
    assert body["authorize_url"].startswith("https://auth.openai.com/oauth/authorize?")
    assert "code_challenge=" in body["authorize_url"]
    assert body["state"] in body["authorize_url"]


def test_oauth_callback_validation(host_client):
    # Missing params
    assert host_client.get("/v1/auth/oauth/codex/callback").status_code == 400
    assert host_client.get("/v1/auth/oauth/google/callback").status_code == 400
    # Unknown state
    r = host_client.get(
        "/v1/auth/oauth/codex/callback", params={"code": "c", "state": "bogus"}
    )
    assert r.status_code == 400
    assert "state" in r.json()["detail"].lower()


def test_claude_setup_token_saved_as_default(host_client):
    r = host_client.post(
        "/v1/auth/claude/setup-token",
        headers=H,
        json={"token": "sk-ant-oat01-abcdefghij"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["profile"]["id"] == "claude-max"
    assert body["profile"]["provider"] == "anthropic"
    assert body["profile"]["method"] == "setup_token"
    assert body["profile"]["has_secret"] is True
    assert "sk-ant-oat01-abcdefghij" not in r.text

    data = host_client.get("/v1/auth/profiles", headers=H).json()
    assert data["default_profile_id"] == "claude-max"


def test_claude_use_cli_sets_local_profile(host_client, monkeypatch):
    from texllm.host import app as app_mod

    monkeypatch.setattr(
        app_mod,
        "probe_cli_auth",
        lambda agent_id: {"agent_id": agent_id, "installed": True, "logged_in": True},
    )
    r = host_client.post("/v1/auth/claude/use-cli", headers=H, json={})
    assert r.status_code == 200
    body = r.json()
    assert body["profile"]["method"] == "local_cli"
    assert body["profile"]["agent_id"] == "claude"
    assert body["cli_status"]["installed"] is True

    data = host_client.get("/v1/auth/profiles", headers=H).json()
    assert data["default_profile_id"] == "claude-cli"


def test_cli_status_endpoint(host_client, monkeypatch):
    from texllm.host import app as app_mod

    monkeypatch.setattr(
        app_mod,
        "probe_cli_auth",
        lambda agent_id: {"agent_id": agent_id, "installed": False, "logged_in": None},
    )
    r = host_client.get("/v1/auth/cli-status/claude", headers=H)
    assert r.status_code == 200
    assert r.json()["agent_id"] == "claude"


def test_chat_uses_mock_provider_and_default_aliases(host_client):
    r = host_client.post("/v1/chat", headers=H, json={"message": "hello there"})
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "assistant"
    assert body["content"]
    assert body["provider"] == "mock"
    assert body["agent_name"] == "Tex"
    assert body["user_name"] == "Operator"


def test_chat_provider_failure_returns_502(host_client, monkeypatch):
    from texllm import providers as providers_mod

    def boom(settings=None):
        raise RuntimeError("provider down")

    monkeypatch.setattr(providers_mod, "get_provider", boom)
    r = host_client.post("/v1/chat", headers=H, json={"message": "hello"})
    assert r.status_code == 502
    assert "provider down" in r.json()["detail"]
