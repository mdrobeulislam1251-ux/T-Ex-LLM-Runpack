"""iMessage via BlueBubbles — the honest iMessage story.

Apple ships no public iMessage API. BlueBubbles (https://bluebubbles.app) is a
community server that runs ON A MAC and relays iMessage in/out. This adapter
speaks its webhook + REST API. Caveats (documented in docs/CHANNELS.md): it is
unofficial, Apple updates can break it, and the "private-api" send method needs
the BlueBubbles helper enabled (fallback: "apple-script").

BlueBubbles webhooks don't sign payloads; auth = the shared server password as
a query parameter, so put the host behind HTTPS or a tailnet. Our own outgoing
messages come back as webhook events with isFromMe=true — skipping them is a
mandatory echo-loop guard.
"""

from __future__ import annotations

import hmac
import json
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import quote
from uuid import uuid4

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

HttpPost = Callable[[str, Dict[str, Any]], Tuple[int, Dict[str, Any]]]

_TIMEOUT = 15.0


def _default_http_post(url: str, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(url, json=payload)
        try:
            body = resp.json()
        except ValueError:
            body = {}
        return resp.status_code, body


@register_adapter
class BlueBubblesAdapter(ChannelAdapter):
    name = "bluebubbles"

    def __init__(
        self,
        *,
        url: str,
        password: str,
        allowed: frozenset = frozenset(),
        http_post: Optional[HttpPost] = None,
    ) -> None:
        self.url = url.rstrip("/")
        self.password = password
        self._allowed = allowed
        self._http_post = http_post or _default_http_post

    @classmethod
    def from_settings(cls, settings: Settings) -> Optional["BlueBubblesAdapter"]:
        url = (settings.bluebubbles_url or "").strip()
        password = (settings.bluebubbles_password or "").strip()
        if not (url and password):
            return None
        return cls(
            url=url,
            password=password,
            allowed=parse_senders(settings.bluebubbles_allowed_senders),
        )

    def verify_and_parse(self, req: WebhookRequest) -> List[InboundMessage]:
        got = req.query.get("password", "")
        if not (self.password and hmac.compare_digest(got, self.password)):
            raise ChannelVerifyError("bluebubbles password mismatch")
        try:
            event = json.loads(req.body.decode("utf-8")) if req.body else {}
        except (ValueError, UnicodeDecodeError) as exc:
            raise ChannelVerifyError("bluebubbles payload is not JSON") from exc

        if event.get("type") != "new-message":
            return []
        data = event.get("data") or {}
        if data.get("isFromMe"):
            return []  # echo-loop guard: our own replies come back as events
        text = data.get("text") or ""
        sender = str((data.get("handle") or {}).get("address") or "")
        chats = data.get("chats") or []
        chat_guid = str((chats[0] if chats else {}).get("guid") or data.get("chatGuid") or "")
        if not (text and sender and chat_guid):
            return []
        return [
            InboundMessage(
                sender_id=sender,
                chat_ref=chat_guid,
                text=text,
                raw={"guid": data.get("guid")},
            )
        ]

    def send(self, chat_ref: str, text: str) -> None:
        url = f"{self.url}/api/v1/message/text?password={quote(self.password)}"
        status, _ = self._http_post(
            url,
            {
                "chatGuid": chat_ref,
                "message": text,
                "method": "private-api",
                "tempGuid": str(uuid4()),
            },
        )
        if status >= 300:
            raise RuntimeError(f"bluebubbles send failed: HTTP {status}")
