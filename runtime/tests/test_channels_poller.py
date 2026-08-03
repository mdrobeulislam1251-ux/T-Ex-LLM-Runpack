"""Telegram long-poll worker — the zero-public-URL transport."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ["TEXLLM_FORCE_MOCK"] = "1"
os.environ["LLM_PROVIDER"] = "mock"

from texllm import config as config_mod
from texllm.channels.base import parse_senders
from texllm.channels.service import ChannelService
from texllm.channels.telegram import TelegramAdapter
from texllm.channels.telegram_poll import TelegramPoller
from texllm.host.store import JobStore


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.chdir(tmp_path)
    config_mod.get_settings.cache_clear()
    from texllm.workspace import db as db_mod

    db_mod._workspace = None  # type: ignore[attr-defined]
    yield
    db_mod._workspace = None  # type: ignore[attr-defined]
    config_mod.get_settings.cache_clear()


def _update(uid: int, text: str) -> dict:
    return {
        "update_id": uid,
        "message": {"from": {"id": 42}, "chat": {"id": 7}, "text": text},
    }


def test_poll_once_advances_offset_and_routes(tmp_path: Path):
    calls = []
    batches = [
        {"ok": True, "result": [_update(5, "help"), _update(6, "teams")]},
        {"ok": True, "result": []},
    ]

    def http_get(url, params, timeout):
        calls.append((url, dict(params)))
        return 200, batches[min(len(calls) - 1, 1)]

    sent = []
    adapter = TelegramAdapter(
        bot_token="TOK",
        allowed=parse_senders("42"),
        http_post=lambda url, payload: (sent.append(payload), (200, {}))[1],
    )
    store = JobStore()
    svc = ChannelService(
        settings=config_mod.Settings(_env_file=None),
        adapters={"telegram": adapter},
        store_getter=lambda: store,
    )
    poller = TelegramPoller(adapter, svc, http_get=http_get)

    assert poller.poll_once() == 2
    assert calls[0][1]["offset"] == 0
    assert poller.poll_once() == 0
    assert calls[1][1]["offset"] == 7  # max update_id + 1

    # both allowlisted commands were answered through the adapter
    texts = [p["text"] for p in sent]
    assert any("run <team>" in t for t in texts)  # help
    assert any("dev" in t for t in texts)  # teams listing


def test_poll_409_raises_actionable_error():
    adapter = TelegramAdapter(bot_token="TOK", http_post=lambda u, p: (200, {}))
    svc = ChannelService(
        settings=config_mod.Settings(_env_file=None),
        adapters={"telegram": adapter},
        store_getter=JobStore,
    )
    poller = TelegramPoller(adapter, svc, http_get=lambda u, p, t: (409, {}))
    with pytest.raises(RuntimeError) as exc:
        poller.poll_once()
    assert "webhook" in str(exc.value).lower()
