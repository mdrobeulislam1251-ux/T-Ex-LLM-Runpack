"""Team runner + firmware tests (mock provider)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Force mock before settings cache
os.environ["LLM_PROVIDER"] = "mock"

from texllm import config as config_mod
from texllm.schemas import Job, JobStatus
from texllm.workers.runner import TeamRunner

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.chdir(ROOT)
    config_mod.get_settings.cache_clear()
    yield
    config_mod.get_settings.cache_clear()


def test_team_job_succeeds():
    settings = config_mod.get_settings()
    settings.firmware_dir = ROOT / "firmware"
    runner = TeamRunner(settings=settings)
    job = Job(
        firmware_id="sample-assistant",
        firmware_version="0.1.0",
        goal="Explain how T-ex LLM team runners work for product integration",
        input={"goal": "Explain how T-ex LLM team runners work for product integration"},
    )
    job = runner.run_job(job)
    assert job.status == JobStatus.succeeded
    assert job.result is not None
    assert job.result.review_passed is True
    assert job.result.iterations >= 3
    assert job.result.handoffs
    assert "answer" in job.result.output or job.result.summary


def test_review_retry_path():
    """Force a weak first draft via special marker then ensure loop handles it.

    Mock reviewer fails on PLACEHOLDER_FAIL; we inject via a custom provider wrap.
    """
    from texllm.providers.mock import MockProvider
    from texllm.providers.base import ChatMessage, CompletionResult

    class Flaky(MockProvider):
        def __init__(self):
            self.n = 0

        def complete(self, messages, *, model=None, temperature=0.2, max_tokens=1024):
            system = " ".join(m.content for m in messages if m.role == "system").lower()
            if "executor" in system:
                self.n += 1
                if self.n == 1:
                    return CompletionResult(
                        content="PLACEHOLDER_FAIL",
                        model="mock",
                        provider="mock",
                        usage_tokens=1,
                    )
            return super().complete(
                messages, model=model, temperature=temperature, max_tokens=max_tokens
            )

    settings = config_mod.get_settings()
    settings.firmware_dir = ROOT / "firmware"
    runner = TeamRunner(provider=Flaky(), settings=settings)
    job = Job(
        firmware_id="sample-assistant",
        firmware_version="0.1.0",
        goal="Write a short product pitch for agentic firmware",
        input={},
    )
    job = runner.run_job(job)
    assert job.status == JobStatus.succeeded
    assert job.result is not None
    assert job.result.review_passed is True
    assert job.result.iterations >= 4


def test_tool_allowlist():
    from texllm.tools.builtin import build_builtin_registry

    reg = build_builtin_registry().allowlist(["echo"])
    assert reg.call("echo", {"text": "hi"}) == {"echo": "hi"}
    with pytest.raises(KeyError):
        reg.call("now", {})
