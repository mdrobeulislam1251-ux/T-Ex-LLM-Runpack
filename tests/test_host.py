"""Host API smoke tests."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["LLM_PROVIDER"] = "mock"
os.environ["HOST_API_KEY"] = "test-key"

from texllm import config as config_mod

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("HOST_API_KEY", "test-key")
    monkeypatch.chdir(ROOT)
    config_mod.get_settings.cache_clear()

    # Reset module-level store
    from texllm.host import app as app_mod

    app_mod.store = app_mod.JobStore()
    # Ensure firmware path
    s = config_mod.get_settings()
    s.firmware_dir = ROOT / "firmware"

    with TestClient(app_mod.app) as c:
        yield c
    config_mod.get_settings.cache_clear()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_and_poll_job(client):
    r = client.post(
        "/v1/jobs",
        headers={"X-API-Key": "test-key"},
        json={
            "firmware_id": "sample-assistant",
            "firmware_version": "0.1.0",
            "goal": "List three benefits of multi-agent workers",
        },
    )
    assert r.status_code == 200
    job = r.json()
    job_id = job["id"]
    assert job["status"] in ("queued", "running", "succeeded")

    # Poll
    final = None
    for _ in range(50):
        g = client.get(f"/v1/jobs/{job_id}", headers={"X-API-Key": "test-key"})
        assert g.status_code == 200
        final = g.json()
        if final["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.05)

    assert final is not None
    assert final["status"] == "succeeded"
    assert final["result"]["review_passed"] is True


def test_auth_required_when_key_set(client):
    r = client.post(
        "/v1/jobs",
        json={"goal": "x"},
    )
    assert r.status_code == 401
