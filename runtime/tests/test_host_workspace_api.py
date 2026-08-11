"""Workspace, runbook, and job/agent endpoint tests against the host API."""

from __future__ import annotations

import os
import time

os.environ["LLM_PROVIDER"] = "mock"
os.environ["HOST_API_KEY"] = "test-key"

H = {"X-API-Key": "test-key"}


def _poll_job(client, job_id: str) -> dict:
    final = {}
    for _ in range(100):
        r = client.get(f"/v1/jobs/{job_id}", headers=H)
        assert r.status_code == 200
        final = r.json()
        if final["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.05)
    return final


# ----- teams -----


def test_create_team_validates_and_normalizes_slug(host_client):
    r = host_client.post("/v1/workspace/teams", headers=H, json={"name": "Support"})
    assert r.status_code == 400

    r = host_client.post(
        "/v1/workspace/teams",
        headers=H,
        json={"slug": "Customer Support", "name": "Support"},
    )
    assert r.status_code == 200
    assert r.json()["slug"] == "customer-support"

    dash = host_client.get("/v1/workspace/teams/customer-support", headers=H)
    assert dash.status_code == 200
    body = dash.json()
    assert body["team"]["slug"] == "customer-support"
    assert body["brains"]
    assert body["kanban"]["columns"]


def test_team_dashboard_unknown_is_404(host_client):
    r = host_client.get("/v1/workspace/teams/no-such-team", headers=H)
    assert r.status_code == 404


# ----- team runs (sync + async dispatch) -----


def test_team_run_validation(host_client):
    assert (
        host_client.post(
            "/v1/workspace/teams/sales/run", headers=H, json={}
        ).status_code
        == 400
    )
    assert (
        host_client.post(
            "/v1/workspace/teams/no-such-team/run", headers=H, json={"goal": "x"}
        ).status_code
        == 404
    )
    assert (
        host_client.post(
            "/v1/workspace/teams/sales/run-async", headers=H, json={}
        ).status_code
        == 400
    )
    assert (
        host_client.post(
            "/v1/workspace/teams/no-such-team/run-async",
            headers=H,
            json={"goal": "x"},
        ).status_code
        == 404
    )


def test_team_run_sync_with_mock_provider(host_client):
    r = host_client.post(
        "/v1/workspace/teams/sales/run",
        headers=H,
        json={"goal": "Draft an outreach plan"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["team"]["slug"] == "sales"
    assert body["status"] == "succeeded"
    assert body["result"]["review_passed"] is True


def test_team_run_async_returns_job_and_completes(host_client):
    r = host_client.post(
        "/v1/workspace/teams/dev/run-async",
        headers=H,
        json={"goal": "Write release notes"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["team"] == "dev"
    assert body["status"] in ("queued", "running", "succeeded")

    final = _poll_job(host_client, body["job_id"])
    assert final["status"] == "succeeded"
    assert final["result"]["review_passed"] is True


def test_personal_bd_requires_goal(host_client):
    r = host_client.post("/v1/workspace/personal-bd/run", headers=H, json={})
    assert r.status_code == 400


def test_domain_review_requires_domain(host_client):
    r = host_client.post("/v1/workspace/domain-review", headers=H, json={})
    assert r.status_code == 400


# ----- brains / skills -----


def test_add_brain_requires_known_team(host_client):
    r = host_client.post(
        "/v1/workspace/brains", headers=H, json={"name": "Closer"}
    )
    assert r.status_code == 400
    r = host_client.post(
        "/v1/workspace/brains",
        headers=H,
        json={"team_slug": "sales", "name": "Closer", "role": "closer"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Closer"


def test_add_skill_with_and_without_team(host_client):
    r = host_client.post(
        "/v1/workspace/skills",
        headers=H,
        json={"team_slug": "sales", "name": "Pitch", "description": "Pitch decks"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Pitch"

    r2 = host_client.post(
        "/v1/workspace/skills", headers=H, json={"name": "Global skill"}
    )
    assert r2.status_code == 200


# ----- kanban / KPIs -----


def test_kanban_add_and_move(host_client):
    assert (
        host_client.post(
            "/v1/workspace/teams/no-such-team/kanban", headers=H, json={"title": "x"}
        ).status_code
        == 404
    )
    assert (
        host_client.post(
            "/v1/workspace/teams/sales/kanban", headers=H, json={}
        ).status_code
        == 400
    )

    card = host_client.post(
        "/v1/workspace/teams/sales/kanban",
        headers=H,
        json={"title": "Call top leads", "column_key": "todo"},
    ).json()

    moved = host_client.post(
        f"/v1/workspace/kanban/{card['id']}/move",
        headers=H,
        json={"column_key": "doing"},
    )
    assert moved.status_code == 200
    assert moved.json()["column_key"] == "doing"

    assert (
        host_client.post(
            "/v1/workspace/kanban/ghost/move", headers=H, json={"column_key": "doing"}
        ).status_code
        == 404
    )
    assert (
        host_client.post(
            f"/v1/workspace/kanban/{card['id']}/move",
            headers=H,
            json={"column_key": "not-a-column"},
        ).status_code
        == 400
    )
    assert (
        host_client.post(
            f"/v1/workspace/kanban/{card['id']}/move", headers=H, json={}
        ).status_code
        == 400
    )


def test_kpi_patch(host_client):
    assert (
        host_client.patch(
            "/v1/workspace/kpis/ghost", headers=H, json={"value": "1"}
        ).status_code
        == 404
    )
    dash = host_client.get("/v1/workspace/teams/sales", headers=H).json()
    kpi_id = dash["kpis"][0]["id"]
    r = host_client.patch(
        f"/v1/workspace/kpis/{kpi_id}", headers=H, json={"value": "42", "trend": "up"}
    )
    assert r.status_code == 200
    assert r.json()["value"] == "42"


# ----- firmware export + listing -----


def test_export_firmware_api_and_listing(host_client, tmp_path):
    assert (
        host_client.post(
            "/v1/workspace/teams/no-such-team/export-firmware", headers=H, json={}
        ).status_code
        == 404
    )

    r = host_client.post(
        "/v1/workspace/teams/sales/export-firmware", headers=H, json={}
    )
    assert r.status_code == 200
    assert r.json()["package_id"] == "sales-agents"
    assert (tmp_path / "firmware" / "sales-agents" / "manifest.yaml").is_file()

    fw = host_client.get("/v1/firmware", headers=H)
    assert fw.status_code == 200
    ids = [f["id"] for f in fw.json()["firmware"]]
    assert "sales-agents" in ids


# ----- runbook -----


def test_runbook_snapshot(host_client):
    r = host_client.get("/v1/runbook", headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body["phases"]
    assert body["progress"]["total"] == len(body["phases"])
    assert body["progress"]["done"] == 0
    assert body["auth_profiles"] == []
    assert body["active_ai"]["name"] == "mock"


def test_runbook_patch_phase(host_client):
    assert (
        host_client.patch(
            "/v1/runbook/phases/no-such-phase", headers=H, json={"status": "done"}
        ).status_code
        == 404
    )
    r = host_client.patch(
        "/v1/runbook/phases/intent",
        headers=H,
        json={"status": "done", "company_name": "Acme"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["company_name"] == "Acme"
    assert body["active_phase"] == "intent"
    intent = next(p for p in body["phases"] if p["id"] == "intent")
    assert intent["status"] == "done"
    assert body["progress"]["done"] >= 1


def test_runbook_run_phase_with_mock_provider(host_client):
    assert (
        host_client.post(
            "/v1/runbook/phases/no-such-phase/run", headers=H, json={}
        ).status_code
        == 404
    )
    r = host_client.post(
        "/v1/runbook/phases/intent/run",
        headers=H,
        json={"company_name": "Acme", "notes": "b2b saas"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["company_name"] == "Acme"
    intent = next(p for p in body["phases"] if p["id"] == "intent")
    assert intent["status"] == "done"
    assert intent["result"]["mode"] == "phase_run"
    assert intent["result"]["provider"] == "mock"
    # Placeholders were filled — no leftover [bracket] values
    for value in intent["placeholder"].values():
        if isinstance(value, str):
            assert not value.startswith("[")


def test_runbook_run_phase_error_fallback_still_advances(host_client, monkeypatch):
    from texllm import providers as providers_mod

    def boom(settings=None):
        raise RuntimeError("no provider available")

    monkeypatch.setattr(providers_mod, "get_provider", boom)
    r = host_client.post("/v1/runbook/phases/product/run", headers=H, json={})
    assert r.status_code == 200
    product = next(p for p in r.json()["phases"] if p["id"] == "product")
    assert product["status"] == "done"
    assert product["result"]["mode"] == "error_fallback"
    assert "no provider available" in product["result"]["error"]


# ----- jobs / agents / system -----


def test_job_requires_goal(host_client):
    r = host_client.post("/v1/jobs", headers=H, json={"input": {}})
    assert r.status_code == 400


def test_job_list_and_cancel(host_client):
    # sample-assistant only ships in the runtime checkout — point the cached
    # settings at it since the fixture chdirs into an empty tmp workspace
    from pathlib import Path

    from texllm import config as config_mod

    config_mod.get_settings().firmware_dir = (
        Path(__file__).resolve().parents[1] / "firmware"
    )

    assert (
        host_client.post("/v1/jobs/ghost/cancel", headers=H).status_code == 404
    )
    created = host_client.post(
        "/v1/jobs",
        headers=H,
        json={
            "firmware_id": "sample-assistant",
            "firmware_version": "0.1.0",
            "goal": "Summarize the workspace",
        },
    ).json()
    final = _poll_job(host_client, created["id"])
    assert final["status"] == "succeeded"

    listed = host_client.get("/v1/jobs", headers=H).json()["jobs"]
    assert any(j["id"] == created["id"] for j in listed)

    # Cancelling a finished job is a no-op, not an error
    r = host_client.post(f"/v1/jobs/{created['id']}/cancel", headers=H)
    assert r.status_code == 200
    assert r.json()["status"] == "succeeded"


def test_agents_run_disabled_returns_403(host_client, monkeypatch):
    monkeypatch.setenv("ALLOW_LOCAL_CLI", "false")
    from texllm import config as config_mod

    config_mod.get_settings.cache_clear()
    r = host_client.post(
        "/v1/agents/run", headers=H, json={"agent_id": "claude", "prompt": "hi"}
    )
    assert r.status_code == 403


def test_agents_run_maps_cli_error_to_400(host_client, monkeypatch):
    from texllm.host import app as app_mod
    from texllm.agents.local_cli import LocalCliError

    def boom(agent_id, prompt, **kwargs):
        raise LocalCliError("agent not found: nope")

    monkeypatch.setattr(app_mod, "run_local_agent", boom)
    r = host_client.post(
        "/v1/agents/run", headers=H, json={"agent_id": "nope", "prompt": "hi"}
    )
    assert r.status_code == 400
    assert "agent not found" in r.json()["detail"]


def test_agents_run_applies_aliases(host_client, monkeypatch):
    from texllm.host import app as app_mod

    captured = {}

    def fake_run(agent_id, prompt, **kwargs):
        captured["prompt"] = prompt
        return {"agent_id": agent_id, "output": "done", "exit_code": 0}

    monkeypatch.setattr(app_mod, "run_local_agent", fake_run)
    r = host_client.post(
        "/v1/agents/run", headers=H, json={"agent_id": "claude", "prompt": "do it"}
    )
    assert r.status_code == 200
    assert r.json()["aliases_applied"] is True
    assert "do it" in captured["prompt"]
    assert "**Tex**" in captured["prompt"]  # alias preamble prepended


def test_system_info_reports_capabilities(host_client):
    r = host_client.get("/v1/system")
    assert r.status_code == 200
    body = r.json()
    assert body["capabilities"]["team_runner"] is True
    assert body["aliases"]["agent_name"] == "Tex"
    assert isinstance(body["agents"], dict)
