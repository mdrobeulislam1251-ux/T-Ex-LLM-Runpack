"""Telegram long-poll worker — drive T-Ex from chat with NO public URL.

    tex channels poll telegram        # foreground worker (Ctrl-C to stop)
    tex channels poll telegram --once # single getUpdates pass (smoke test)

Or opt in on the host: TELEGRAM_POLL_ON_SERVE=true starts a daemon thread in
`texllm serve` (only when a bot token is set and no webhook secret is
configured — webhook and getUpdates are mutually exclusive in Telegram).

Caveat (docs/CHANNELS.md): a standalone poller process and a `serve` process
each own an independent in-memory JobStore — chat `status`/`jobs` only see
jobs dispatched through the same process. Run one or the other.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple

import httpx

from texllm.channels.service import ChannelService
from texllm.channels.telegram import TelegramAdapter

logger = logging.getLogger(__name__)

HttpGet = Callable[[str, Dict[str, Any], float], Tuple[int, Dict[str, Any]]]


def _default_http_get(
    url: str, params: Dict[str, Any], timeout: float
) -> Tuple[int, Dict[str, Any]]:
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(url, params=params)
        try:
            body = resp.json()
        except ValueError:
            body = {}
        return resp.status_code, body


class TelegramPoller:
    def __init__(
        self,
        adapter: TelegramAdapter,
        service: ChannelService,
        http_get: Optional[HttpGet] = None,
        poll_timeout: int = 50,
    ) -> None:
        self.adapter = adapter
        self.service = service
        self._http_get = http_get or _default_http_get
        self.poll_timeout = poll_timeout
        self._offset = 0

    def poll_once(self) -> int:
        """One getUpdates round trip. Returns the number of updates handled."""
        url = f"{self.adapter.api_base}/bot{self.adapter.bot_token}/getUpdates"
        params = {
            "timeout": self.poll_timeout,
            "offset": self._offset,
            "allowed_updates": json.dumps(["message"]),
        }
        status, body = self._http_get(url, params, float(self.poll_timeout + 10))
        if status == 409:
            raise RuntimeError(
                "telegram getUpdates returned 409 — a webhook is registered for "
                "this bot; call deleteWebhook (or use webhook mode) before polling"
            )
        if status != 200 or not body.get("ok", False):
            raise RuntimeError(f"telegram getUpdates failed: HTTP {status}")

        updates = body.get("result") or []
        for update in updates:
            update_id = update.get("update_id")
            if isinstance(update_id, int):
                self._offset = max(self._offset, update_id + 1)
            messages = self.adapter.parse_update(update)
            if messages:
                self.service.deliver("telegram", messages)
        return len(updates)

    def run_forever(self, stop: Optional[threading.Event] = None) -> None:
        """Loop poll_once with backoff on transient errors. The 409
        webhook-conflict error is re-raised — it needs operator action."""
        delay = 2.0
        while stop is None or not stop.is_set():
            try:
                self.poll_once()
                delay = 2.0
            except RuntimeError as exc:
                if "409" in str(exc) or "webhook" in str(exc).lower():
                    raise
                logger.warning("telegram poll error: %s (retry in %.0fs)", exc, delay)
                time.sleep(delay)
                delay = min(delay * 2, 30.0)
            except Exception:  # noqa: BLE001 — network blips must not kill the worker
                logger.warning("telegram poll error (retry in %.0fs)", delay, exc_info=True)
                time.sleep(delay)
                delay = min(delay * 2, 30.0)


def start_poller_thread(service: ChannelService) -> Optional[threading.Thread]:
    """Opt-in autostart used by `texllm serve` (TELEGRAM_POLL_ON_SERVE=true)."""
    adapter = service.adapter("telegram")
    if not isinstance(adapter, TelegramAdapter):
        logger.warning("TELEGRAM_POLL_ON_SERVE set but telegram is not configured")
        return None
    poller = TelegramPoller(adapter, service)
    thread = threading.Thread(
        target=poller.run_forever, name="telegram-poller", daemon=True
    )
    thread.start()
    logger.info("telegram long-poll worker started (in-process)")
    return thread
