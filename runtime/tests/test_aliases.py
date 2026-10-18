"""Agent alias store + API tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["LLM_PROVIDER"] = "mock"
os.environ["HOST_API_KEY"] = "test-key"

from texllm.host.aliases import AgentAliases, AliasStore


def test_alias_store_roundtrip(tmp_path: Path):
    store = AliasStore(path=tmp_path / "aliases.json")
    saved = store.set(
        AgentAliases(
            agent_name="Alli",
            user_name="Robeul",
            agent_aliases=["Assistant"],
            user_aliases=["boss"],
        )
    )
    assert saved.agent_name == "Alli"
    assert store.get().user_name == "Robeul"
    assert "Address the user as **Robeul**" in store.get().prompt_preamble()


def test_aliases_api(tmp_path: Path, monkeypatch):
    from texllm.host import aliases as aliases_mod
    from texllm.host import app as app_mod
    from texllm import config as config_mod

    monkeypatch.chdir(tmp_path)
    config_mod.get_settings.cache_clear()
    monkeypatch.setenv("HOST_API_KEY", "test-key")
    config_mod.get_settings.cache_clear()

    aliases_mod.alias_store = AliasStore(path=tmp_path / "a.json")

    with TestClient(app_mod.app) as client:
        r = client.get("/v1/settings/aliases", headers={"X-API-Key": "test-key"})
        assert r.status_code == 200
        assert r.json()["agent_name"] == "Tex"

        r2 = client.put(
            "/v1/settings/aliases",
            headers={"X-API-Key": "test-key"},
            json={
                "agent_name": "Alli",
                "user_name": "Captain",
                "agent_aliases": ["Bot"],
                "user_aliases": ["Chief"],
            },
        )
        assert r2.status_code == 200
        body = r2.json()
        assert body["agent_name"] == "Alli"
        assert body["user_name"] == "Captain"

        r3 = client.patch(
            "/v1/settings/aliases",
            headers={"X-API-Key": "test-key"},
            json={"user_name": "Skipper"},
        )
        assert r3.status_code == 200
        assert r3.json()["user_name"] == "Skipper"
        assert r3.json()["agent_name"] == "Alli"
