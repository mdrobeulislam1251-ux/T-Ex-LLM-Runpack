"""Per-platform adapter tests: verification (the auth edge), parsing, sending.

Every adapter is exercised with inline fixture payloads and injected fake
transports — no network, no secrets. Wrong-signature cases are as important
as happy paths: these endpoints sit OUTSIDE the host API key gate.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os

import pytest

os.environ["TEXLLM_FORCE_MOCK"] = "1"

from texllm.channels.base import (
    ChannelVerifyError,
    InboundMessage,
    WebhookRequest,
    parse_senders,
)
from texllm.channels.bluebubbles import BlueBubblesAdapter
from texllm.channels.custom import CustomAdapter
from texllm.channels.google_chat import GoogleChatAdapter
from texllm.channels.registry import build_adapters, registered_names
from texllm.channels.telegram import TelegramAdapter
from texllm.channels.whatsapp import WhatsAppAdapter
from texllm.config import Settings


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


# ---------------------------------------------------------------- Telegram

def _tg(secret="s3", **kw):
    return TelegramAdapter(
        bot_token="TOK",
        webhook_secret=secret,
        allowed=parse_senders("42"),
        http_post=kw.pop("http_post", None),
    )


def _tg_update(text="hello", sender=42, chat=-100123):
    return {
        "update_id": 7,
        "message": {
            "message_id": 1,
            "from": {"id": sender, "is_bot": False},
            "chat": {"id": chat, "type": "group"},
            "text": text,
        },
    }


def test_telegram_good_secret_parses():
    req = WebhookRequest(
        body=json.dumps(_tg_update()).encode(),
        headers={"x-telegram-bot-api-secret-token": "s3"},
    )
    msgs = _tg().verify_and_parse(req)
    assert len(msgs) == 1
    assert msgs[0].sender_id == "42"
    assert msgs[0].chat_ref == "-100123"
    assert msgs[0].text == "hello"


def test_telegram_wrong_or_missing_secret():
    body = json.dumps(_tg_update()).encode()
    with pytest.raises(ChannelVerifyError):
        _tg().verify_and_parse(
            WebhookRequest(body=body, headers={"x-telegram-bot-api-secret-token": "nope"})
        )
    with pytest.raises(ChannelVerifyError):
        _tg().verify_and_parse(WebhookRequest(body=body, headers={}))


def test_telegram_webhook_disabled_without_secret():
    with pytest.raises(ChannelVerifyError):
        _tg(secret="").verify_and_parse(
            WebhookRequest(body=b"{}", headers={"x-telegram-bot-api-secret-token": ""})
        )


def test_telegram_non_text_update_ignored():
    update = {"update_id": 8, "message": {"from": {"id": 42}, "chat": {"id": 1}, "photo": []}}
    req = WebhookRequest(
        body=json.dumps(update).encode(),
        headers={"x-telegram-bot-api-secret-token": "s3"},
    )
    assert _tg().verify_and_parse(req) == []


def test_telegram_send_posts_to_bot_api():
    sent = []

    def capture(url, payload):
        sent.append((url, payload))
        return 200, {"ok": True}

    _tg(http_post=capture).send("-100123", "done")
    url, payload = sent[0]
    assert "/botTOK/sendMessage" in url
    assert payload == {"chat_id": "-100123", "text": "done"}


def test_telegram_from_settings_none_without_token():
    assert TelegramAdapter.from_settings(_settings()) is None
    a = TelegramAdapter.from_settings(
        _settings(telegram_bot_token="t", telegram_allowed_senders="42, 43")
    )
    assert a is not None
    assert a.allowed_senders() == frozenset({"42", "43"})


# ---------------------------------------------------------------- WhatsApp

def _wa(**kw):
    return WhatsAppAdapter(
        access_token="AT",
        app_secret="as",
        verify_token="vt",
        phone_number_id="555000",
        allowed=parse_senders("15551234567"),
        http_post=kw.pop("http_post", None),
    )


def _wa_body(text="run dev x", sender="15551234567") -> bytes:
    return json.dumps(
        {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {"from": sender, "type": "text", "text": {"body": text}}
                                ]
                            }
                        }
                    ]
                }
            ]
        }
    ).encode()


def _wa_sig(body: bytes, secret: str = "as") -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_whatsapp_valid_signature_parses():
    body = _wa_body()
    req = WebhookRequest(body=body, headers={"x-hub-signature-256": _wa_sig(body)})
    msgs = _wa().verify_and_parse(req)
    assert len(msgs) == 1
    assert msgs[0].sender_id == "15551234567"
    assert msgs[0].chat_ref == "15551234567"
    assert msgs[0].text == "run dev x"


def test_whatsapp_tampered_body_rejected():
    body = _wa_body()
    sig = _wa_sig(body)
    with pytest.raises(ChannelVerifyError):
        _wa().verify_and_parse(
            WebhookRequest(body=body + b" ", headers={"x-hub-signature-256": sig})
        )


def test_whatsapp_status_only_payload_ignored():
    body = json.dumps(
        {"entry": [{"changes": [{"value": {"statuses": [{"status": "delivered"}]}}]}]}
    ).encode()
    req = WebhookRequest(body=body, headers={"x-hub-signature-256": _wa_sig(body)})
    assert _wa().verify_and_parse(req) == []


def test_whatsapp_get_handshake():
    ok = _wa().handle_get(
        WebhookRequest(
            method="GET",
            query={"hub.mode": "subscribe", "hub.verify_token": "vt", "hub.challenge": "123"},
        )
    )
    assert ok.status_code == 200
    assert ok.text == "123"

    bad = _wa().handle_get(
        WebhookRequest(
            method="GET",
            query={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "1"},
        )
    )
    assert bad.status_code == 403


def test_whatsapp_from_settings_requires_triple():
    assert WhatsAppAdapter.from_settings(_settings(whatsapp_access_token="x")) is None
    a = WhatsAppAdapter.from_settings(
        _settings(
            whatsapp_access_token="x",
            whatsapp_app_secret="y",
            whatsapp_phone_number_id="1",
        )
    )
    assert a is not None


# ---------------------------------------------------------------- Google Chat

def _gc(http_get=None, space_webhook_url=""):
    return GoogleChatAdapter(
        project_number="999",
        allowed=parse_senders("users/111, boss@example.com"),
        space_webhook_url=space_webhook_url,
        http_get=http_get
        or (lambda url, params: (200, {"iss": "chat@system.gserviceaccount.com", "aud": "999"})),
    )


def _gc_event(text="teams", argument_text=None, user="users/111", email="boss@example.com"):
    msg = {"text": text}
    if argument_text is not None:
        msg["argumentText"] = argument_text
    return {
        "type": "MESSAGE",
        "message": msg,
        "user": {"name": user, "email": email},
        "space": {"name": "spaces/AAA"},
    }


def test_google_chat_valid_jwt_parses():
    req = WebhookRequest(
        body=json.dumps(_gc_event(text="@Tex teams", argument_text=" teams")).encode(),
        headers={"authorization": "Bearer JWT"},
    )
    msgs = _gc().verify_and_parse(req)
    assert len(msgs) == 1
    assert msgs[0].sender_id == "users/111"
    assert msgs[0].chat_ref == "spaces/AAA"
    assert msgs[0].text == "teams"  # argumentText preferred, stripped


def test_google_chat_wrong_audience_rejected():
    bad = _gc(http_get=lambda u, p: (200, {"iss": "chat@system.gserviceaccount.com", "aud": "1"}))
    req = WebhookRequest(body=b"{}", headers={"authorization": "Bearer JWT"})
    with pytest.raises(ChannelVerifyError):
        bad.verify_and_parse(req)


def test_google_chat_tokeninfo_failure_rejected():
    bad = _gc(http_get=lambda u, p: (400, {}))
    req = WebhookRequest(body=b"{}", headers={"authorization": "Bearer JWT"})
    with pytest.raises(ChannelVerifyError):
        bad.verify_and_parse(req)


def test_google_chat_missing_auth_header():
    with pytest.raises(ChannelVerifyError):
        _gc().verify_and_parse(WebhookRequest(body=b"{}", headers={}))


def test_google_chat_email_allowlist_match():
    adapter = _gc()
    msg_by_email = InboundMessage(
        sender_id="users/222", chat_ref="spaces/AAA", text="x", raw={"email": "boss@example.com"}
    )
    msg_unknown = InboundMessage(sender_id="users/222", chat_ref="spaces/AAA", text="x", raw={})
    assert adapter.is_allowed(msg_by_email) is True
    assert adapter.is_allowed(msg_unknown) is False


def test_google_chat_push_only_with_space_webhook():
    assert _gc().can_push is False
    assert _gc(space_webhook_url="https://chat.googleapis.com/x").can_push is True


# ---------------------------------------------------------------- BlueBubbles

def _bb(http_post=None):
    return BlueBubblesAdapter(
        url="http://mac.local:1234",
        password="pw",
        allowed=parse_senders("+15551234567"),
        http_post=http_post,
    )


def _bb_body(text="help", is_from_me=False):
    return json.dumps(
        {
            "type": "new-message",
            "data": {
                "text": text,
                "isFromMe": is_from_me,
                "handle": {"address": "+15551234567"},
                "chats": [{"guid": "iMessage;-;+15551234567"}],
            },
        }
    ).encode()


def test_bluebubbles_password_verifies():
    msgs = _bb().verify_and_parse(
        WebhookRequest(body=_bb_body(), query={"password": "pw"})
    )
    assert len(msgs) == 1
    assert msgs[0].sender_id == "+15551234567"
    assert msgs[0].chat_ref == "iMessage;-;+15551234567"


def test_bluebubbles_wrong_password():
    with pytest.raises(ChannelVerifyError):
        _bb().verify_and_parse(WebhookRequest(body=_bb_body(), query={"password": "no"}))


def test_bluebubbles_own_echo_skipped():
    msgs = _bb().verify_and_parse(
        WebhookRequest(body=_bb_body(is_from_me=True), query={"password": "pw"})
    )
    assert msgs == []


def test_bluebubbles_send_hits_text_api():
    sent = []

    def capture(url, payload):
        sent.append((url, payload))
        return 200, {}

    _bb(http_post=capture).send("iMessage;-;+15551234567", "done")
    url, payload = sent[0]
    assert "/api/v1/message/text" in url
    assert payload["chatGuid"] == "iMessage;-;+15551234567"
    assert payload["message"] == "done"
    assert payload["tempGuid"]


# ---------------------------------------------------------------- Custom HMAC

def _cu(http_post=None):
    return CustomAdapter(
        secret="cs", allowed=parse_senders("ops-bot"), http_post=http_post
    )


def _cu_body(reply_url="https://hooks.example.com/r1"):
    payload = {"sender": "ops-bot", "text": "run dev x"}
    if reply_url:
        payload["reply_url"] = reply_url
    return json.dumps(payload).encode()


def _cu_sig(body: bytes, prefix="") -> str:
    return prefix + hmac.new(b"cs", body, hashlib.sha256).hexdigest()


def test_custom_signature_with_and_without_prefix():
    body = _cu_body()
    for prefix in ("", "sha256="):
        msgs = _cu().verify_and_parse(
            WebhookRequest(body=body, headers={"x-tex-channel-signature": _cu_sig(body, prefix)})
        )
        assert msgs[0].sender_id == "ops-bot"
        assert msgs[0].chat_ref == "https://hooks.example.com/r1"


def test_custom_bad_signature():
    body = _cu_body()
    with pytest.raises(ChannelVerifyError):
        _cu().verify_and_parse(
            WebhookRequest(body=body, headers={"x-tex-channel-signature": "deadbeef"})
        )


def test_custom_send_signs_outbound():
    sent = []

    def capture(url, body_bytes, headers):
        sent.append((url, body_bytes, headers))
        return 200, {}

    _cu(http_post=capture).send("https://hooks.example.com/r1", "done")
    url, body_bytes, headers = sent[0]
    assert url == "https://hooks.example.com/r1"
    expected = hmac.new(b"cs", body_bytes, hashlib.sha256).hexdigest()
    assert headers["X-Tex-Channel-Signature"] == expected


def test_custom_send_requires_http_url():
    with pytest.raises(RuntimeError):
        _cu(http_post=lambda *a: (200, {})).send("not-a-url", "x")


# ---------------------------------------------------------------- Registry

def test_builtins_registered():
    names = registered_names()
    for expected in ("telegram", "whatsapp", "google_chat", "bluebubbles", "custom"):
        assert expected in names


def test_build_adapters_only_configured():
    adapters = build_adapters(_settings(telegram_bot_token="t"))
    assert set(adapters) == {"telegram"}
    assert build_adapters(_settings()) == {}
