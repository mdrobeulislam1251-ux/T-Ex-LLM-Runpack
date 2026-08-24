"""No silent mock: unconfigured provider must fail loudly, mock is opt-in only."""

from __future__ import annotations

from pathlib import Path

import pytest

from texllm.host.credentials import CredentialStore
from texllm.providers.base import ProviderNotConfiguredError
from texllm.providers.mock import MockProvider


@pytest.fixture
def unconfigured(tmp_path: Path, monkeypatch):
    """Nothing connected: no forced mock, no env key, empty credential store."""
    monkeypatch.chdir(tmp_path)  # keep Settings from reading the repo's .env
    monkeypatch.delenv("TEXLLM_FORCE_MOCK", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    from texllm import config as config_mod
    from texllm.host import credentials as cred_mod

    config_mod.get_settings.cache_clear()
    monkeypatch.setattr(
        cred_mod, "credential_store", CredentialStore(path=tmp_path / "c.json")
    )
    yield
    config_mod.get_settings.cache_clear()


def test_unconfigured_provider_raises_not_mock(unconfigured):
    from texllm.providers import get_provider

    with pytest.raises(ProviderNotConfiguredError) as exc:
        get_provider()
    # The error must be actionable, pointing at the real connection paths
    msg = str(exc.value)
    assert "claude setup-token" in msg
    assert "LLM_PROVIDER=mock" in msg


def test_explicit_mock_env_still_works(unconfigured, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    from texllm import config as config_mod
    from texllm.providers import get_provider

    config_mod.get_settings.cache_clear()
    assert isinstance(get_provider(), MockProvider)


def test_force_mock_env_still_works(unconfigured, monkeypatch):
    monkeypatch.setenv("TEXLLM_FORCE_MOCK", "1")
    from texllm.providers import get_provider

    assert isinstance(get_provider(), MockProvider)


def test_describe_active_provider_reports_unconfigured(unconfigured):
    from texllm.providers import describe_active_provider

    out = describe_active_provider()
    assert out["name"] == "none"
    assert out["usable"] is False
    assert "claude setup-token" in out["hint"]


def test_unconfigured_team_job_fails_with_actionable_error(unconfigured):
    """The job record carries the failure — never a mock 'succeeded'."""
    from texllm import config as config_mod
    from texllm.schemas import Job, JobStatus
    from texllm.workers.runner import TeamRunner

    settings = config_mod.get_settings()
    settings.firmware_dir = Path(__file__).resolve().parents[1] / "firmware"
    runner = TeamRunner(settings=settings)  # lazy provider: no raise here
    job = Job(
        firmware_id="sample-assistant",
        firmware_version="0.1.0",
        goal="Anything",
        input={},
    )
    job = runner.run_job(job)
    assert job.status == JobStatus.failed
    assert job.result is None
    assert "No AI provider configured" in (job.error or "")
