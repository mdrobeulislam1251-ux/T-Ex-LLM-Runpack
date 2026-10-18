"""Shared test config: never let the suite touch a real provider.

Provider resolution is Claude-CLI-first (texllm.providers.get_provider), so on any
machine with a `claude` binary the suite would otherwise shell out to it — spending
real tokens where a login works, or failing where the CLI refuses to run (e.g. as
root). TEXLLM_FORCE_MOCK is checked before everything else in get_provider(); set
it for every test so the suite is deterministic and offline on all machines.
"""

from __future__ import annotations

import os

import pytest

os.environ["TEXLLM_FORCE_MOCK"] = "1"


@pytest.fixture
def host_client(tmp_path, monkeypatch):
    """TestClient with every host singleton rebound under tmp_path.

    The host resolves all state (.texllm/, firmware/, .env) against the CWD, and
    keeps process-wide singletons: credential_store, alias_store, the workspace
    DB, the runbook state, and the job store. Reset each one so tests are
    order-independent and never touch the repo checkout.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOST_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    from texllm import config as config_mod

    config_mod.get_settings.cache_clear()

    from texllm.host import app as app_mod
    from texllm.host import credentials as cred_mod
    from texllm.runbook import state as runbook_state
    from texllm.workspace import db as db_mod

    # app.py holds its own reference to the credential store, and
    # resolve_runtime() reads the module global — patch the app's object and
    # point the global at it so both names agree even if an earlier test
    # rebound the module global.
    monkeypatch.setattr(
        app_mod.credential_store, "path", tmp_path / ".texllm" / "credentials.json"
    )
    monkeypatch.setattr(app_mod.credential_store, "_data", None)
    monkeypatch.setattr(cred_mod, "credential_store", app_mod.credential_store)
    monkeypatch.setattr(
        app_mod.alias_store, "path", tmp_path / ".texllm" / "aliases.json"
    )
    monkeypatch.setattr(app_mod.alias_store, "_cache", None)
    db_mod._workspace = None
    runbook_state.reset_runbook_singleton()
    app_mod.store = app_mod.JobStore()

    from fastapi.testclient import TestClient

    with TestClient(app_mod.app) as client:
        yield client

    config_mod.get_settings.cache_clear()
    db_mod._workspace = None
    runbook_state.reset_runbook_singleton()

