"""Google Chat adapter.

Inbound: a Chat app configured with an HTTP endpoint POSTs MESSAGE events with
an `Authorization: Bearer <JWT>` header. v1 verifies the JWT via Google's
tokeninfo endpoint (one HTTPS round-trip per event; needs egress) — offline
verification with google-auth is a documented optional follow-up, keeping the
hard-dependency set unchanged.

Replies are SYNCHRONOUS: the ack rides back as {"text": ...} in the HTTP
response, so no outbound call is needed. Completion pushes are only possible
when GOOGLE_CHAT_SPACE_WEBHOOK_URL (a space "incoming webhook") is configured.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx

from texllm.channels.base import (
    ChannelAdapter,
    ChannelVerifyError,
    InboundMessage,
    WebhookRequest,
    parse_senders,
)
from texllm.channels.registry import register_adapter
from texllm.config import Settings

HttpGet = Callable[[str, Dict[str, str]], Tuple[int, Dict[str, Any]]]
HttpPost = Callable[[str, Dict[str, Any]], Tuple[int, Dict[str, Any]]]

_TIMEOUT = 10.0
_CHAT_ISSUER = "chat@system.gserviceaccount.com"


def _default_http_get(url: str, params: Dict[str, str]) -> Tuple[int, Dict[str, Any]]:
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.get(url, params=params)
        try:
            body = resp.json()
        except ValueError:
            body = {}
        return resp.status_code, body


def _default_http_post(url: str, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(url, json=payload)
        try:
            body = resp.json()
        except ValueError:
            body = {}
        return resp.status_code, body


@register_adapter
class GoogleChatAdapter(ChannelAdapter):
    name = "google_chat"
    supports_sync_reply = True

    def __init__(
        self,
        *,
        project_number: str,
        allowed: frozenset = frozenset(),
        space_webhook_url: str = "",
        tokeninfo_url: str = "https://oauth2.googleapis.com/tokeninfo",
        http_get: Optional[HttpGet] = None,
        http_post: Optional[HttpPost] = None,
    ) -> None:
        self.project_number = project_number
        self._allowed = allowed
        self.space_webhook_url = space_webhook_url
        self.tokeninfo_url = tokeninfo_url
        self._http_get = http_get or _default_http_get
        self._http_post = http_post or _default_http_post

    @classmethod
    def from_settings(cls, settings: Settings) -> Optional["GoogleChatAdapter"]:
        project = (settings.google_chat_project_number or "").strip()
        if not project:
            return None
        return cls(
            project_number=project,
            allowed=parse_senders(settings.google_chat_allowed_senders),
            space_webhook_url=(settings.google_chat_space_webhook_url or "").strip(),
            tokeninfo_url=settings.google_chat_tokeninfo_url,
        )

    def verify_and_parse(self, req: WebhookRequest) -> List[InboundMessage]:
        auth = req.headers.get("authorization", "")
        if not auth.lower().startswith("bearer "):
            raise ChannelVerifyError("google chat: missing bearer token")
        token = auth[7:].strip()
        status, claims = self._http_get(self.tokeninfo_url, {"id_token": token})
        if status != 200:
            raise ChannelVerifyError("google chat: tokeninfo rejected the token")
        if claims.get("iss") != _CHAT_ISSUER or str(claims.get("aud")) != self.project_number:
            raise ChannelVerifyError("google chat: issuer/audience mismatch")

        try:
            event = json.loads(req.body.decode("utf-8")) if req.body else {}
        except (ValueError, UnicodeDecodeError) as exc:
            raise ChannelVerifyError("google chat payload is not JSON") from exc

        if event.get("type") != "MESSAGE":
            return []
        message = event.get("message") or {}
        user = event.get("user") or {}
        space = event.get("space") or {}
        # argumentText is the message with the @mention already stripped
        text = message.get("argumentText")
        if text is None:
            text = message.get("text") or ""
        text = text.strip()
        if not text:
            return []
        return [
            InboundMessage(
                sender_id=str(user.get("name") or ""),
                chat_ref=str(space.get("name") or ""),
                text=text,
                raw={"email": user.get("email") or ""},
            )
        ]

    def is_allowed(self, msg: InboundMessage) -> bool:
        if super().is_allowed(msg):
            return True
        email = str(msg.raw.get("email") or "").strip().casefold()
        return bool(email) and email in self._allowed

    @property
    def can_push(self) -> bool:
        return bool(self.space_webhook_url)

    def send(self, chat_ref: str, text: str) -> None:
        if not self.space_webhook_url:
            raise RuntimeError(
                "google chat push needs GOOGLE_CHAT_SPACE_WEBHOOK_URL (incoming webhook)"
            )
        status, _ = self._http_post(self.space_webhook_url, {"text": text})
        if status >= 300:
            raise RuntimeError(f"google chat push failed: HTTP {status}")
