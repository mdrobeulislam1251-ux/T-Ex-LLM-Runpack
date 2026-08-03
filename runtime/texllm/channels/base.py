"""Messaging-channel adapter contract.

A channel adapter turns platform webhooks (or poll results) into normalized
inbound messages and can push replies back. Third parties subclass
ChannelAdapter, call registry.register_adapter, and point CHANNEL_PLUGINS at
their module — no core files change.

Security invariants every adapter must keep:
- verify_and_parse authenticates the request with the PLATFORM's mechanism
  (signature/secret/JWT) using hmac.compare_digest for comparisons — webhook
  endpoints are deliberately outside the host X-API-Key gate.
- Secrets come from Settings (env) and are never logged or echoed.
- describe() reports counts/flags only, never secret values.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import BaseModel, Field

from texllm.config import Settings


class ChannelVerifyError(Exception):
    """Platform verification failed — the HTTP layer answers 401 (403 for
    WhatsApp's GET handshake) with a generic detail, never the received value."""


@dataclass
class WebhookRequest:
    """Raw inbound webhook, as the adapter needs it (HMAC needs exact bytes)."""

    body: bytes = b""
    headers: Dict[str, str] = field(default_factory=dict)  # keys lower-cased
    query: Dict[str, str] = field(default_factory=dict)
    method: str = "POST"


@dataclass
class WebhookResponse:
    """Transport-neutral response the HTTP layer renders."""

    status_code: int = 200
    json_body: Optional[Dict[str, Any]] = None
    text: Optional[str] = None  # plain-text body (WhatsApp hub.challenge echo)


class InboundMessage(BaseModel):
    sender_id: str
    chat_ref: str  # opaque reply-routing token (chat id / chatGuid / reply_url)
    text: str
    channel: str = ""  # stamped by the service
    raw: Dict[str, Any] = Field(default_factory=dict)


def parse_senders(raw: str) -> frozenset:
    """Comma-separated allowlist → frozenset of stripped, casefolded entries."""
    return frozenset(
        part.strip().casefold()
        for part in (raw or "").split(",")
        if part.strip()
    )


class ChannelAdapter(ABC):
    """One messaging platform. Instances are built from Settings only."""

    name: ClassVar[str] = ""
    supports_sync_reply: ClassVar[bool] = False

    _allowed: frozenset = frozenset()

    @classmethod
    @abstractmethod
    def from_settings(cls, settings: Settings) -> Optional["ChannelAdapter"]:
        """Return a configured adapter, or None when its enabling env vars are
        unset (the channel then simply doesn't exist on this host)."""

    @abstractmethod
    def verify_and_parse(self, req: WebhookRequest) -> List[InboundMessage]:
        """Authenticate the request and extract text messages.

        Raise ChannelVerifyError on bad auth. Return [] for verified but
        ignorable events (delivery statuses, non-text, our own echoes)."""

    def handle_get(self, req: WebhookRequest) -> WebhookResponse:
        """Platform GET handshakes (WhatsApp). Default: not supported."""
        return WebhookResponse(status_code=405, json_body={"detail": "GET not supported"})

    @property
    def can_push(self) -> bool:
        """Whether send() can deliver an out-of-band message."""
        return True

    def send(self, chat_ref: str, text: str) -> None:
        raise NotImplementedError(f"{self.name} adapter cannot push messages")

    def allowed_senders(self) -> frozenset:
        return self._allowed

    def is_allowed(self, msg: InboundMessage) -> bool:
        """Default-deny dispatch gate. Empty allowlist = nobody may dispatch.
        Adapters may override to match extra identities (e.g. email)."""
        return msg.sender_id.strip().casefold() in self._allowed

    def describe(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "configured": True,
            "allowed_senders": len(self.allowed_senders()),
            "sync_reply": self.supports_sync_reply,
            "can_push": self.can_push,
        }
