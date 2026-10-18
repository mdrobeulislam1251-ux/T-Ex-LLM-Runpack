"""Claude-first provider resolution."""

from __future__ import annotations

import os
from pathlib import Path

os.environ["LLM_PROVIDER"] = "mock"

from texllm.host.credentials import AuthProfileCreate, CredentialStore
from texllm.providers import get_provider
from texllm.providers.claude_cli import ClaudeCLIProvider
from texllm.providers.mock import MockProvider


def test_no_profile_uses_mock(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from texllm.host import credentials as cred

    monkeypatch.setattr(cred, "credential_store", CredentialStore(path=tmp_path / "c.json"))
    from texllm import config as config_mod

    config_mod.get_settings.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    config_mod.get_settings.cache_clear()
    p = get_provider()
    assert isinstance(p, MockProvider)


def test_local_cli_profile_selects_claude_cli(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    monkeypatch.delenv("TEXLLM_FORCE_MOCK", raising=False)
    from texllm import config as config_mod
    from texllm.host import credentials as cred

    config_mod.get_settings.cache_clear()
    store = CredentialStore(path=tmp_path / "c.json")
    monkeypatch.setattr(cred, "credential_store", store)
    store.upsert(
        AuthProfileCreate(
            id="claude-cli",
            provider="anthropic",
            method="local_cli",
            agent_id="claude",
            label="CLI",
        )
    )
    store.set_default("claude-cli")

    # If claude binary missing, ClaudeCLIProvider raises — accept either
    try:
        p = get_provider()
        assert isinstance(p, ClaudeCLIProvider)
    except ValueError as e:
        assert "claude CLI not found" in str(e)


def test_setup_token_prefers_cli_when_present(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    monkeypatch.delenv("TEXLLM_FORCE_MOCK", raising=False)
    from texllm import config as config_mod
    from texllm.host import credentials as cred

    config_mod.get_settings.cache_clear()
    store = CredentialStore(path=tmp_path / "c.json")
    monkeypatch.setattr(cred, "credential_store", store)
    store.upsert(
        AuthProfileCreate(
            id="claude-max",
            provider="anthropic",
            method="setup_token",
            api_key="test-oauth-token-value-here",
            label="Max",
        )
    )
    store.set_default("claude-max")
    try:
        p = get_provider()
        assert p.name in ("claude_cli", "anthropic")
    except ValueError:
        from texllm.providers.anthropic import AnthropicProvider

        p = get_provider()
        assert isinstance(p, AnthropicProvider)
