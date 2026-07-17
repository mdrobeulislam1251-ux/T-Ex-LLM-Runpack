"""Workspace DB + API smoke."""

from __future__ import annotations

import os
from pathlib import Path

os.environ["LLM_PROVIDER"] = "mock"
os.environ["HOST_API_KEY"] = "test-key"

from fastapi.testclient import TestClient


def test_workspace_seed_and_custom_team(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from texllm.workspace.db import WorkspaceDB

    db = WorkspaceDB(path=tmp_path / "w.db")
    teams = db.list_teams()
    slugs = {t["slug"] for t in teams}
    assert "ops" in slugs
    assert "sales" in slugs
    assert "personal-bd" in slugs

    t = db.create_team(slug="support", name="Support", description="Tickets")
    assert t["slug"] == "support"
    dash = db.dashboard("support")
    assert dash["brains"]
    assert dash["flows"]


def test_workspace_api(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOST_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    from texllm import config as config_mod
    from texllm.workspace import db as db_mod

    config_mod.get_settings.cache_clear()
    db_mod._workspace = None  # type: ignore[attr-defined]

    from texllm.host import app as app_mod

    with TestClient(app_mod.app) as client:
        r = client.get("/v1/workspace", headers={"X-API-Key": "test-key"})
        assert r.status_code == 200
        body = r.json()
        assert body["team_count"] >= 7

        r2 = client.get(
            "/v1/workspace/teams/sales", headers={"X-API-Key": "test-key"}
        )
        assert r2.status_code == 200
        assert r2.json()["team"]["slug"] == "sales"
