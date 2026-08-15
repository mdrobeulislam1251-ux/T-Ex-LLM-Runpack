"""Chat-mode agent sessions + per-team memory (NanoClaw model).

When Claude is connected, the executor stage of a chat run is one full
headless Claude session in the team's persistent memory dir — not a
single-shot completion. Mock/test setups keep the classic loop.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ["TEXLLM_FORCE_MOCK"] = "1"
os.environ["LLM_PROVIDER"] = "mock"

from texllm import config as config_mod
from texllm.providers.mock import MockProvider
from texllm.schemas import Job, JobStatus
from texllm.workers.code_executor import CodeExecutor
from texllm.workers.runner import TeamRunner

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.chdir(tmp_path)
    config_mod.get_settings.cache_clear()
    yield
    config_mod.get_settings.cache_clear()


def _settings(tmp_path: Path):
    s = config_mod.get_settings()
    s.firmware_dir = ROOT / "firmware"
    s.code_runs_dir = tmp_path / "runs"
    s.team_memory_dir = tmp_path / "teams"
    return s


def fake_session_cmd(answer: str, seen: dict):
    """Mimic `claude -p --output-format json` for a chat session."""

    def run_cmd(argv, cwd, env, timeout):
        seen["argv"] = argv
        seen["cwd"] = cwd
        return 0, json.dumps({"result": answer}), ""

    return run_cmd


# ----- per-team memory (prepare_team_job) -----


def test_prepare_team_job_writes_team_memory(tmp_path: Path):
    from texllm.workspace.db import WorkspaceDB
    from texllm.workspace.team_run import prepare_team_job

    settings = _settings(tmp_path)
    db = WorkspaceDB(path=tmp_path / "w.db")
    sales = db.get_team("sales")
    db.add_brain(sales["id"], "Closer", role="closer", prompt="Close enterprise deals")
    db.add_skill("Pitch", description="Pitch decks", team_id=sales["id"])

    team, job = prepare_team_job("sales", "Draft outreach", db=db)
    mem = Path(job.input["memory_dir"])
    assert mem == settings.team_memory_dir / "sales"
    claude_md = (mem / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Closer" in claude_md
    assert "Pitch" in claude_md
    assert "notes.md" in claude_md  # durable-notes contract is documented


def test_code_mode_gets_no_memory_dir(tmp_path: Path):
    from texllm.workspace.db import WorkspaceDB
    from texllm.workspace.team_run import prepare_team_job

    _settings(tmp_path)
    db = WorkspaceDB(path=tmp_path / "w.db")
    _, job = prepare_team_job("dev", "Fix bug", db=db, mode="code")
    assert "memory_dir" not in job.input


def test_memory_regeneration_preserves_notes(tmp_path: Path):
    from texllm.workspace.db import WorkspaceDB
    from texllm.workspace.team_run import prepare_team_job

    settings = _settings(tmp_path)
    db = WorkspaceDB(path=tmp_path / "w.db")
    prepare_team_job("sales", "First run", db=db)
    notes = settings.team_memory_dir / "sales" / "notes.md"
    notes.write_text("Remember: client prefers Tuesdays\n", encoding="utf-8")
    prepare_team_job("sales", "Second run", db=db)
    # CLAUDE.md is regenerated; the agent's own notes are never touched
    assert "Tuesdays" in notes.read_text(encoding="utf-8")


# ----- session gating -----


def test_sessions_disabled_under_forced_mock(tmp_path: Path):
    runner = TeamRunner(settings=_settings(tmp_path), provider=MockProvider())
    assert runner._chat_sessions_enabled() is False


def test_sessions_enabled_with_claude_connected(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("TEXLLM_FORCE_MOCK", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    config_mod.get_settings.cache_clear()
    from texllm.host import credentials as cred_mod

    monkeypatch.setattr(
        cred_mod, "resolve_runtime", lambda: {"method": "setup_token"}
    )
    runner = TeamRunner(settings=_settings(tmp_path), provider=MockProvider())
    assert runner._chat_sessions_enabled() is True


def test_sessions_respect_config_off_switch(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("TEXLLM_FORCE_MOCK", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    monkeypatch.setenv("CHAT_AGENT_SESSIONS", "false")
    config_mod.get_settings.cache_clear()
    from texllm.host import credentials as cred_mod

    monkeypatch.setattr(
        cred_mod, "resolve_runtime", lambda: {"method": "setup_token"}
    )
    runner = TeamRunner(settings=_settings(tmp_path), provider=MockProvider())
    assert runner._chat_sessions_enabled() is False


# ----- session execution -----


def test_chat_run_uses_agent_session_in_memory_dir(tmp_path: Path, monkeypatch):
    settings = _settings(tmp_path)
    mem = tmp_path / "teams" / "sales"
    seen: dict = {}
    executor = CodeExecutor(
        settings=settings,
        run_cmd=fake_session_cmd(
            "Session answer: a three-step Q3 outreach plan with owners and dates.",
            seen,
        ),
    )
    monkeypatch.setattr(TeamRunner, "_chat_sessions_enabled", lambda self: True)
    runner = TeamRunner(
        settings=settings, provider=MockProvider(), code_executor=executor
    )
    job = Job(
        firmware_id="sample-assistant",
        firmware_version="0.1.0",
        goal="Draft the Q3 outreach plan",
        input={"memory_dir": str(mem)},
    )
    job = runner.run_job(job)

    assert job.status == JobStatus.succeeded, job.error
    assert job.result.output["mode"] == "agent_session"
    assert job.result.output["memory_dir"] == str(mem)
    # The session ran in the memory dir and its text became the deliverable
    assert seen["cwd"] == str(mem)
    assert "-p" in seen["argv"]
    assert "Session answer" in json.dumps(job.result.output)
    assert job.result.review_passed is True


def test_chat_session_failure_fails_job(tmp_path: Path, monkeypatch):
    settings = _settings(tmp_path)

    def broken(argv, cwd, env, timeout):
        return 1, "", "claude: authentication expired"

    executor = CodeExecutor(settings=settings, run_cmd=broken)
    monkeypatch.setattr(TeamRunner, "_chat_sessions_enabled", lambda self: True)
    runner = TeamRunner(
        settings=settings, provider=MockProvider(), code_executor=executor
    )
    job = Job(
        firmware_id="sample-assistant",
        firmware_version="0.1.0",
        goal="Anything",
        input={"memory_dir": str(tmp_path / "teams" / "dev")},
    )
    job = runner.run_job(job)
    assert job.status == JobStatus.failed
    assert "chat agent session failed" in (job.error or "")
    assert "authentication expired" in (job.error or "")


def test_chat_without_session_keeps_classic_loop(tmp_path: Path):
    """Forced-mock (tests/demo) chat runs are unchanged: no session, no workdir."""
    settings = _settings(tmp_path)
    runner = TeamRunner(settings=settings, provider=MockProvider())
    job = Job(
        firmware_id="sample-assistant",
        firmware_version="0.1.0",
        goal="Explain the runner",
        input={},
    )
    job = runner.run_job(job)
    assert job.status == JobStatus.succeeded
    assert job.result.output.get("mode") != "agent_session"
