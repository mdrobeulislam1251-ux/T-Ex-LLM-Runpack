"""dispatch_team_job — the queue-and-run helper shared by /run-async and channels."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

os.environ["TEXLLM_FORCE_MOCK"] = "1"
os.environ["LLM_PROVIDER"] = "mock"

from texllm import config as config_mod
from texllm.host.dispatch import dispatch_team_job
from texllm.host.store import JobStore
from texllm.schemas import JobStatus


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.chdir(tmp_path)
    config_mod.get_settings.cache_clear()
    yield
    config_mod.get_settings.cache_clear()


def _wait_terminal(store: JobStore, job_id: str, tries: int = 200):
    for _ in range(tries):
        job = store.get(job_id)
        if job and job.status in (JobStatus.succeeded, JobStatus.failed):
            return job
        time.sleep(0.05)
    raise AssertionError("job never reached a terminal state")


def test_dispatch_returns_queued_and_completes(tmp_path: Path):
    from texllm.workspace.db import WorkspaceDB

    db = WorkspaceDB()
    store = JobStore()
    team, job = dispatch_team_job("dev", "Draft the checklist", store=store, db=db)

    assert team["slug"] == "dev"
    assert job.mode == "chat"
    assert store.get(job.id) is not None  # queued synchronously

    final = _wait_terminal(store, job.id)
    assert final.status == JobStatus.succeeded
    assert final.result is not None


def test_on_done_receives_final_job_once(tmp_path: Path):
    from texllm.workspace.db import WorkspaceDB

    db = WorkspaceDB()
    store = JobStore()
    seen = []
    _, job = dispatch_team_job(
        "dev",
        "Draft notes",
        store=store,
        db=db,
        on_done=lambda j: seen.append(j),
    )
    _wait_terminal(store, job.id)
    for _ in range(100):
        if seen:
            break
        time.sleep(0.05)
    assert len(seen) == 1
    assert seen[0].status == JobStatus.succeeded
    assert seen[0].id == job.id


def test_on_done_exception_does_not_corrupt_job(tmp_path: Path):
    from texllm.workspace.db import WorkspaceDB

    db = WorkspaceDB()
    store = JobStore()

    def boom(_j):
        raise RuntimeError("push failed")

    _, job = dispatch_team_job("dev", "Draft notes", store=store, db=db, on_done=boom)
    final = _wait_terminal(store, job.id)
    assert final.status == JobStatus.succeeded  # push failure never touches job state


def test_unknown_team_raises_keyerror(tmp_path: Path):
    from texllm.workspace.db import WorkspaceDB

    db = WorkspaceDB()
    store = JobStore()
    with pytest.raises(KeyError):
        dispatch_team_job("no-such-team", "goal", store=store, db=db)
