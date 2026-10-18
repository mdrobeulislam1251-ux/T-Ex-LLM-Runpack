"""Webhook endpoints over the real FastAPI app.

The load-bearing assertions: webhook routes work WITHOUT X-API-Key (platform
signature is the auth), bad signatures get 401, and the status endpoint never
leaks a secret value.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["TEXLLM_FORCE_MOCK"] = "1"
os.environ["LLM_PROVIDER"] = "mock"

from texllm import config as config_mod
from texllm.channels import service as service_mod
from texllm.channels.base import parse_senders
from texllm.channels.service import ChannelService
from texllm.channels.telegram import TelegramAdapter
from texllm.channels.whatsapp import WhatsAppAdapter

KEY = {"X-API-Key": "test-key"}


@pytest.fixture
def deck(monkeypatch, tmp_path: Path):
    """TestClient + captured outbound sends, fully offline."""
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("HOST_API_KEY", "test-key")
    monkeypatch.chdir(tmp_path)
    config_mod.get_settings.cache_clear()

    from texllm.host import app as app_mod
    from texllm.workspace import db as db_mod

    db_mod._workspace = None  # type: ignore[attr-defined]
    app_mod.store = app_mod.JobStore()

    tg_sent = []

    def tg_post(url, payload):
        tg_sent.append((url, payload))
        return 200, {"ok": True}

    telegram = TelegramAdapter(
        bot_token="TOK",
        webhook_secret="s3",
        allowed=parse_senders("42"),
        http_post=tg_post,
    )
    whatsapp = WhatsAppAdapter(
        access_token="AT",
        app_secret="as",
        verify_token="vt",
        phone_number_id="555",
        allowed=parse_senders("15551234567"),
        http_post=lambda url, payload, headers: (200, {}),
    )
    svc = ChannelService(
        settings=config_mod.get_settings(),
        adapters={"telegram": telegram, "whatsapp": whatsapp},
    )
    service_mod._service = svc  # install the fixture singleton

    with TestClient(app_mod.app) as client:
        yield client, tg_sent

    service_mod.reset_channel_service()
    db_mod._workspace = None  # type: ignore[attr-defined]
    config_mod.get_settings.cache_clear()


def _tg_update(text: str) -> dict:
    return {
        "update_id": 1,
        "message": {
            "from": {"id": 42},
            "chat": {"id": -1001},
            "text": text,
        },
    }


def test_telegram_webhook_dispatches_without_api_key(deck):
    client, tg_sent = deck
    r = client.post(
        "/v1/channels/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "s3"},  # note: NO X-API-Key
        json=_tg_update("run dev Ship the notes"),
    )
    assert r.status_code == 200, r.text

    # ack went out through the adapter
    assert any("Queued chat run on dev" in p.get("text", "") for _, p in tg_sent)

    # job really exists on the host (API-key-gated surface)
    jobs = client.get("/v1/jobs", headers=KEY).json()["jobs"]
    assert len(jobs) == 1

    # completion push arrives when the mock run finishes (drain the thread)
    for _ in range(200):
        if len(tg_sent) >= 2:
            break
        time.sleep(0.05)
    assert any("[dev]" in p.get("text", "") for _, p in tg_sent)


def test_telegram_wrong_secret_401(deck):
    client, tg_sent = deck
    r = client.post(
        "/v1/channels/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
        json=_tg_update("run dev x"),
    )
    assert r.status_code == 401
    assert tg_sent == []
    assert client.get("/v1/jobs", headers=KEY).json()["jobs"] == []


def test_whatsapp_get_handshake(deck):
    client, _ = deck
    ok = client.get(
        "/v1/channels/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "vt", "hub.challenge": "12345"},
    )
    assert ok.status_code == 200
    assert ok.text == "12345"  # raw text echo, not JSON

    bad = client.get(
        "/v1/channels/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "1"},
    )
    assert bad.status_code == 403


def test_channels_status_gated_and_no_secret_leaks(deck):
    client, _ = deck
    assert client.get("/v1/channels").status_code == 401

    r = client.get("/v1/channels", headers=KEY)
    assert r.status_code == 200
    names = [c["name"] for c in r.json()["channels"]]
    assert "telegram" in names and "whatsapp" in names
    # secret VALUES must never appear in the status surface
    assert "s3" not in r.text
    assert "TOK" not in r.text
    assert "as" not in json.dumps(r.json()["channels"])


def test_unknown_channel_404(deck):
    client, _ = deck
    r = client.post("/v1/channels/ghost/webhook", json={})
    assert r.status_code == 404
