"""Code-mode executor tests — the runner must produce real file changes, not prose.

The executor drives a headless coding agent (`claude -p`) in a per-run workdir. Tests
inject a fake agent command so the suite stays offline and deterministic: the fake
writes files into the workdir exactly like a real agent edit would, and the runner
must surface those changes as diff/files-changed artifacts that the reviewer sees.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

os.environ["TEXLLM_FORCE_MOCK"] = "1"
os.environ["LLM_PROVIDER"] = "mock"

from texllm import config as config_mod
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
    return s


def fake_agent_cmd(writes: dict[str, str], summary: str = "Wrote the files."):
    """Return a run_cmd callable that mimics `claude -p --output-format json`."""

    def run_cmd(argv, cwd, env, timeout):
        for rel, content in writes.items():
            target = Path(cwd) / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return 0, json.dumps({"result": summary}), ""

    return run_cmd


def test_code_mode_produces_real_diff_artifacts(tmp_path: Path):
    settings = _settings(tmp_path)
    executor = CodeExecutor(
        settings=settings,
        run_cmd=fake_agent_cmd(
            {"hello.py": "print('hello from the real executor')\n"},
            summary="Created hello.py with a greeting.",
        ),
    )
    runner = TeamRunner(settings=settings, code_executor=executor)
    job = Job(
        firmware_id="sample-assistant",
        firmware_version="0.1.0",
        goal="Create hello.py that prints a greeting",
        input={"goal": "Create hello.py that prints a greeting"},
        mode="code",
    )
    job = runner.run_job(job)

    assert job.status == JobStatus.succeeded, job.error
    assert job.result is not None
    assert job.result.review_passed is True

    # Real changes surfaced, not prose: files list + unified diff artifacts
    assert "hello.py" in job.result.output.get("files_changed", [])
    kinds = {a.name: a for a in job.result.artifacts}
    assert "diff" in kinds
    assert "hello.py" in str(kinds["diff"].content)
    assert "files_changed" in kinds

    # The run happened in an isolated per-job workdir under code_runs_dir
    workdir = Path(job.result.output["workdir"])
    assert workdir.is_dir()
    assert (settings.code_runs_dir in workdir.parents) or (
        workdir == settings.code_runs_dir
    )
    assert (workdir / "hello.py").is_file()


def test_reviewer_sees_the_diff_not_just_prose(tmp_path: Path):
    """The draft handed to the reviewer must contain the actual change."""
    settings = _settings(tmp_path)
    executor = CodeExecutor(
        settings=settings,
        run_cmd=fake_agent_cmd({"src/api.py": "def handler():\n    return 'ok'\n"}),
    )
    runner = TeamRunner(settings=settings, code_executor=executor)
    job = Job(
        firmware_id="sample-assistant",
        firmware_version="0.1.0",
        goal="Add an api handler",
        input={},
        mode="code",
    )
    job = runner.run_job(job)
    assert job.status == JobStatus.succeeded, job.error
    reviewer_handoffs = [
        h for h in job.result.handoffs if h.from_role.value == "executor"
    ]
    assert reviewer_handoffs
    assert "src/api.py" in json.dumps(
        [h.data for h in reviewer_handoffs]
    ) or "src/api.py" in (job.result.output.get("diff") or "")


def test_explicit_workdir_is_used_in_place(tmp_path: Path):
    settings = _settings(tmp_path)
    project = tmp_path / "myproject"
    project.mkdir()
    (project / "README.md").write_text("# existing\n", encoding="utf-8")

    executor = CodeExecutor(
        settings=settings,
        run_cmd=fake_agent_cmd({"fix.txt": "patched\n"}),
    )
    runner = TeamRunner(settings=settings, code_executor=executor)
    job = Job(
        firmware_id="sample-assistant",
        firmware_version="0.1.0",
        goal="Patch the project",
        input={"workdir": str(project)},
        mode="code",
    )
    job = runner.run_job(job)
    assert job.status == JobStatus.succeeded, job.error
    assert job.result.output["workdir"] == str(project)
    assert (project / "fix.txt").is_file()
    assert "fix.txt" in job.result.output.get("files_changed", [])


def test_code_mode_without_agent_fails_honestly(tmp_path: Path):
    """No claude CLI → the job must FAIL with a clear error, never fall back to prose."""
    settings = _settings(tmp_path)
    executor = CodeExecutor(settings=settings, agent_bin="definitely-not-a-real-bin-xyz")
    runner = TeamRunner(settings=settings, code_executor=executor)
    job = Job(
        firmware_id="sample-assistant",
        firmware_version="0.1.0",
        goal="Anything",
        input={},
        mode="code",
    )
    job = runner.run_job(job)
    assert job.status == JobStatus.failed
    assert job.error and "code mode" in job.error.lower()


def test_verify_gate_passes_when_command_exits_zero(tmp_path: Path):
    """The done-gate: job succeeds because the REAL verify command passed."""
    settings = _settings(tmp_path)
    executor = CodeExecutor(
        settings=settings,
        run_cmd=fake_agent_cmd({"hello.py": "print('hi')\n"}),
    )
    runner = TeamRunner(settings=settings, code_executor=executor)
    job = Job(
        firmware_id="sample-assistant",
        firmware_version="0.1.0",
        goal="Create hello.py",
        input={"verify": "test -f hello.py"},
        mode="code",
    )
    job = runner.run_job(job)
    assert job.status == JobStatus.succeeded, job.error
    verify = job.result.output["verify"]
    assert verify["ok"] is True
    assert verify["exit_code"] == 0
    assert verify["command"] == "test -f hello.py"


def test_verify_gate_failure_fails_job_despite_passing_review(tmp_path: Path):
    """Model approval is never 'done': a failing verify command fails the job."""
    settings = _settings(tmp_path)
    executor = CodeExecutor(
        settings=settings,
        run_cmd=fake_agent_cmd({"hello.py": "print('hi')\n"}),
    )
    runner = TeamRunner(settings=settings, code_executor=executor)
    job = Job(
        firmware_id="sample-assistant",
        firmware_version="0.1.0",
        goal="Create something that satisfies an impossible check",
        input={"verify": "test -f does-not-exist.txt"},
        mode="code",
    )
    job = runner.run_job(job)
    # Mock reviewer approves the diff draft, but the machine gate must win
    assert job.status == JobStatus.failed
    assert "verification gate failed" in (job.error or "")
    assert "does-not-exist.txt" in (job.error or "")


def test_chat_mode_unchanged(tmp_path: Path):
    """Default mode stays the text loop — no workdir, no executor requirement."""
    settings = _settings(tmp_path)
    runner = TeamRunner(settings=settings)
    job = Job(
        firmware_id="sample-assistant",
        firmware_version="0.1.0",
        goal="Explain the runner",
        input={},
    )
    job = runner.run_job(job)
    assert job.status == JobStatus.succeeded
    assert job.mode == "chat"
    assert "workdir" not in (job.result.output or {})


def test_host_run_async_endpoint(tmp_path: Path, monkeypatch):
    """Dashboard dispatch path: POST run-async → job_id → poll /v1/jobs/{id}."""
    from fastapi.testclient import TestClient

    monkeypatch.setenv("HOST_API_KEY", "test-key")
    monkeypatch.chdir(tmp_path)
    config_mod.get_settings.cache_clear()

    from texllm.host import app as app_mod
    from texllm.workspace import db as db_mod

    db_mod._workspace = None  # type: ignore[attr-defined] — pin singleton to this dir
    app_mod.store = app_mod.JobStore()

    with TestClient(app_mod.app) as client:
        r = client.post(
            "/v1/workspace/teams/dev/run-async",
            headers={"X-API-Key": "test-key"},
            json={"goal": "Draft the release checklist"},
        )
        assert r.status_code == 200, r.text
        job_id = r.json()["job_id"]
        assert job_id

        final = None
        for _ in range(100):
            g = client.get(f"/v1/jobs/{job_id}", headers={"X-API-Key": "test-key"})
            assert g.status_code == 200
            final = g.json()
            if final["status"] in ("succeeded", "failed"):
                break
            time.sleep(0.05)

        assert final is not None
        assert final["status"] == "succeeded", final.get("error")
        assert final["result"]["review_passed"] is True
