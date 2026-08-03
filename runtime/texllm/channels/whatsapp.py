"""WhatsApp adapter — Meta Cloud API.

Inbound: Meta POSTs message events, signed with X-Hub-Signature-256
(HMAC-SHA256 of the raw body using the app secret). The one-time GET
handshake echoes hub.challenge when hub.verify_token matches.
Outbound: Graph API /<PHONE_NUMBER_ID>/messages with a Bearer access token.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx

from texllm.channels.base import (
    ChannelAdapter,
    ChannelVerifyError,
    InboundMessage,
    WebhookRequest,
    WebhookResponse,
    parse_senders,
)
from texllm.channels.registry import register_adapter
from texllm.config import Settings

HttpPost = Callable[[str, Dict[str, Any], Dict[str, str]], Tuple[int, Dict[str, Any]]]

_TIMEOUT = 10.0


def _default_http_post(
    url: str, payload: Dict[str, Any], headers: Dict[str, str]
) -> Tuple[int, Dict[str, Any]]:
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(url, json=payload, headers=headers)
        try:
            body = resp.json()
        except ValueError:
            body = {}
        return resp.status_code, body


@register_adapter
class WhatsAppAdapter(ChannelAdapter):
    name = "whatsapp"

    def __init__(
        self,
        *,
        access_token: str,
        app_secret: str,
        verify_token: str = "",
        phone_number_id: str,
        allowed: frozenset = frozenset(),
        api_base: str = "https://graph.facebook.com",
        api_version: str = "v21.0",
        http_post: Optional[HttpPost] = None,
    ) -> None:
        self.access_token = access_token
        self.app_secret = app_secret
        self.verify_token = verify_token
        self.phone_number_id = phone_number_id
        self._allowed = allowed
        self.api_base = api_base.rstrip("/")
        self.api_version = api_version
        self._http_post = http_post or _default_http_post

    @classmethod
    def from_settings(cls, settings: Settings) -> Optional["WhatsAppAdapter"]:
        token = (settings.whatsapp_access_token or "").strip()
        secret = (settings.whatsapp_app_secret or "").strip()
        phone_id = (settings.whatsapp_phone_number_id or "").strip()
        if not (token and secret and phone_id):
            return None
        return cls(
            access_token=token,
            app_secret=secret,
            verify_token=(settings.whatsapp_verify_token or "").strip(),
            phone_number_id=phone_id,
            allowed=parse_senders(settings.whatsapp_allowed_senders),
            api_base=settings.whatsapp_api_base,
            api_version=settings.whatsapp_api_version,
        )

    def handle_get(self, req: WebhookRequest) -> WebhookResponse:
        mode = req.query.get("hub.mode", "")
        token = req.query.get("hub.verify_token", "")
        challenge = req.query.get("hub.challenge", "")
        if (
            mode == "subscribe"
            and self.verify_token
            and hmac.compare_digest(token, self.verify_token)
        ):
            return WebhookResponse(status_code=200, text=challenge)
        return WebhookResponse(status_code=403, json_body={"detail": "verification failed"})

    def verify_and_parse(self, req: WebhookRequest) -> List[InboundMessage]:
        expected = (
            "sha256=" + hmac.new(self.app_secret.encode(), req.body, hashlib.sha256).hexdigest()
        )
        got = req.headers.get("x-hub-signature-256", "")
        if not hmac.compare_digest(got, expected):
            raise ChannelVerifyError("whatsapp signature mismatch")
        try:
            payload = json.loads(req.body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise ChannelVerifyError("whatsapp payload is not JSON") from exc

        messages: List[InboundMessage] = []
        for entry in payload.get("entry") or []:
            for change in entry.get("changes") or []:
                value = change.get("value") or {}
                for m in value.get("messages") or []:
                    if m.get("type") != "text":
                        continue
                    sender = str(m.get("from") or "")
                    text = (m.get("text") or {}).get("body") or ""
                    if not sender or not text:
                        continue
                    messages.append(
                        InboundMessage(
                            sender_id=sender,
                            chat_ref=sender,
                            text=text,
                            raw={"id": m.get("id")},
                        )
                    )
        return messages

    def send(self, chat_ref: str, text: str) -> None:
        url = f"{self.api_base}/{self.api_version}/{self.phone_number_id}/messages"
        status, _ = self._http_post(
            url,
            {
                "messaging_product": "whatsapp",
                "to": chat_ref,
                "type": "text",
                "text": {"body": text},
            },
            {"Authorization": f"Bearer {self.access_token}"},
        )
        if status >= 300:
            raise RuntimeError(f"whatsapp send failed: HTTP {status}")
