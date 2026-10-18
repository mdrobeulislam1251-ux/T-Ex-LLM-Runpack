"""Telegram adapter — the reference channel.

Two transports share this adapter:
- webhook: POST /v1/channels/telegram/webhook, verified via the
  X-Telegram-Bot-Api-Secret-Token header (set with setWebhook secret_token).
  No TELEGRAM_WEBHOOK_SECRET configured → the webhook path is hard-disabled.
- long-poll: telegram_poll.TelegramPoller calls parse_update() directly —
  no public URL and no webhook secret needed (the recommended quickstart).

URLs embed the bot token — never log them.
"""

from __future__ import annotations

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

HttpPost = Callable[[str, Dict[str, Any]], Tuple[int, Dict[str, Any]]]

_TIMEOUT = 10.0


def _default_http_post(url: str, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(url, json=payload)
        try:
            body = resp.json()
        except ValueError:
            body = {}
        return resp.status_code, body


@register_adapter
class TelegramAdapter(ChannelAdapter):
    name = "telegram"

    def __init__(
        self,
        *,
        bot_token: str,
        webhook_secret: str = "",
        allowed: frozenset = frozenset(),
        api_base: str = "https://api.telegram.org",
        http_post: Optional[HttpPost] = None,
    ) -> None:
        self.bot_token = bot_token
        self.webhook_secret = webhook_secret
        self._allowed = allowed
        self.api_base = api_base.rstrip("/")
        self._http_post = http_post or _default_http_post

    @classmethod
    def from_settings(cls, settings: Settings) -> Optional["TelegramAdapter"]:
        token = (settings.telegram_bot_token or "").strip()
        if not token:
            return None
        return cls(
            bot_token=token,
            webhook_secret=(settings.telegram_webhook_secret or "").strip(),
            allowed=parse_senders(settings.telegram_allowed_senders),
            api_base=settings.telegram_api_base,
        )

    def verify_and_parse(self, req: WebhookRequest) -> List[InboundMessage]:
        if not self.webhook_secret:
            raise ChannelVerifyError(
                "telegram webhook disabled (TELEGRAM_WEBHOOK_SECRET unset) — "
                "use `tex channels poll telegram` instead"
            )
        got = req.headers.get("x-telegram-bot-api-secret-token", "")
        if not hmac.compare_digest(got, self.webhook_secret):
            raise ChannelVerifyError("telegram secret token mismatch")
        try:
            update = json.loads(req.body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise ChannelVerifyError("telegram payload is not JSON") from exc
        return self.parse_update(update)

    def parse_update(self, update: Dict[str, Any]) -> List[InboundMessage]:
        """Shared by webhook and long-poll paths. Text messages only (v1)."""
        message = update.get("message") or {}
        text = message.get("text")
        sender = (message.get("from") or {}).get("id")
        chat = (message.get("chat") or {}).get("id")
        if not text or sender is None or chat is None:
            return []
        return [
            InboundMessage(
                sender_id=str(sender),
                chat_ref=str(chat),
                text=text,
                raw={"update_id": update.get("update_id")},
            )
        ]

    def send(self, chat_ref: str, text: str) -> None:
        url = f"{self.api_base}/bot{self.bot_token}/sendMessage"
        status, _ = self._http_post(url, {"chat_id": chat_ref, "text": text})
        if status >= 300:
            raise RuntimeError(f"telegram sendMessage failed: HTTP {status}")
