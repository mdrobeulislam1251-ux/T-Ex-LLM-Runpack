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
    assert dash["kpis"]
    assert dash["kanban"]["columns"]
    assert dash["stats"]["brains"] >= 1

    card = db.add_kanban_card(t["id"], "Test card", column_key="todo")
    moved = db.move_kanban_card(card["id"], "doing")
    assert moved["column_key"] == "doing"


def test_export_firmware(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from texllm.workspace.db import WorkspaceDB
    from texllm.workspace.export_firmware import export_team_firmware

    db = WorkspaceDB(path=tmp_path / "w.db")
    sales = db.get_team("sales")
    assert sales
    db.add_brain(sales["id"], "Closer", role="closer", prompt="Close deals")
    db.add_skill("Pitch", description="Pitch deck", team_id=sales["id"], body="steps")

    out = export_team_firmware(
        "sales", version="0.1.0", firmware_root=tmp_path / "firmware", db=db
    )
    assert out["package_id"] == "sales-agents"
    assert out["brains_exported"] >= 2
    man = tmp_path / "firmware" / "sales-agents" / "manifest.yaml"
    assert man.is_file()
    assert (tmp_path / "firmware" / "sales-agents" / "prompts" / "planner.md").is_file()


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
