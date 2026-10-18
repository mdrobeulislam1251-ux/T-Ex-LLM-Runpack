"""Generic custom channel — the reference third-party adapter.

Contract for any tool that wants to be a T-Ex channel:

    POST /v1/channels/custom/webhook
    X-Tex-Channel-Signature: [sha256=]<hex hmac-sha256(CUSTOM_CHANNEL_SECRET, raw_body)>
    {"sender": "ops-bot", "text": "run dev fix X",
     "chat_ref": "...optional...", "reply_url": "https://.../optional"}

The ack rides back synchronously as {"text": ...}. When reply_url is present,
the run-completion push is POSTed there as {"text": ...} with the same
signature header computed over the outbound body — verify us symmetrically.

To write a full adapter instead (own verification/transport): subclass
ChannelAdapter, call register_adapter(YourAdapter) at import time, and set
CHANNEL_PLUGINS=your.module — see docs/CHANNELS.md "Extending".
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
    parse_senders,
)
from texllm.channels.registry import register_adapter
from texllm.config import Settings

HttpPost = Callable[[str, bytes, Dict[str, str]], Tuple[int, Dict[str, Any]]]

_TIMEOUT = 10.0
_SIG_HEADER = "X-Tex-Channel-Signature"


def _default_http_post(
    url: str, body: bytes, headers: Dict[str, str]
) -> Tuple[int, Dict[str, Any]]:
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(url, content=body, headers=headers)
        try:
            parsed = resp.json()
        except ValueError:
            parsed = {}
        return resp.status_code, parsed


@register_adapter
class CustomAdapter(ChannelAdapter):
    name = "custom"
    supports_sync_reply = True

    def __init__(
        self,
        *,
        secret: str,
        allowed: frozenset = frozenset(),
        http_post: Optional[HttpPost] = None,
    ) -> None:
        self.secret = secret
        self._allowed = allowed
        self._http_post = http_post or _default_http_post

    @classmethod
    def from_settings(cls, settings: Settings) -> Optional["CustomAdapter"]:
        secret = (settings.custom_channel_secret or "").strip()
        if not secret:
            return None
        return cls(
            secret=secret,
            allowed=parse_senders(settings.custom_channel_allowed_senders),
        )

    def _signature(self, body: bytes) -> str:
        return hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()

    def verify_and_parse(self, req: WebhookRequest) -> List[InboundMessage]:
        got = req.headers.get(_SIG_HEADER.lower(), "")
        if got.startswith("sha256="):
            got = got[len("sha256="):]
        if not hmac.compare_digest(got, self._signature(req.body)):
            raise ChannelVerifyError("custom channel signature mismatch")
        try:
            payload = json.loads(req.body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise ChannelVerifyError("custom channel payload is not JSON") from exc

        sender = str(payload.get("sender") or "").strip()
        text = str(payload.get("text") or "")
        if not sender or not text:
            return []
        chat_ref = str(payload.get("reply_url") or payload.get("chat_ref") or "")
        return [InboundMessage(sender_id=sender, chat_ref=chat_ref, text=text)]

    def send(self, chat_ref: str, text: str) -> None:
        if not chat_ref.startswith(("http://", "https://")):
            raise RuntimeError("custom channel push needs an http(s) reply_url")
        body = json.dumps({"text": text}).encode("utf-8")
        status, _ = self._http_post(
            chat_ref,
            body,
            {_SIG_HEADER: self._signature(body), "Content-Type": "application/json"},
        )
        if status >= 300:
            raise RuntimeError(f"custom channel push failed: HTTP {status}")
