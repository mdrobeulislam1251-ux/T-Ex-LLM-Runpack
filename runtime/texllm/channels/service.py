"""ChannelService — the router between chat messages and team runs.

One instance serves every configured adapter. Flow per inbound message:
platform-verified parse (adapter) → default-deny allowlist gate → command
grammar → dispatch_team_job (the same path /run-async uses) → ack now,
completion pushed back to the originating chat when the job finishes.

Security posture:
- Unallowlisted senders are dropped SILENTLY (no reply = no probing oracle).
- Verification failures answer a generic 401 — never echo what was received.
- Always HTTP 200 after successful verification, so platforms don't retry-storm.
"""

from __future__ import annotations

import logging
import threading
from functools import partial
from typing import Any, Callable, Dict, List, Optional

from texllm.channels.base import (
    ChannelAdapter,
    ChannelVerifyError,
    InboundMessage,
    WebhookRequest,
    WebhookResponse,
)
from texllm.channels.commands import (
    HELP_TEXT,
    CommandError,
    ParsedCommand,
    parse_command,
)
from texllm.channels.registry import build_adapters, registered_names
from texllm.config import Settings, get_settings
from texllm.host.dispatch import dispatch_team_job
from texllm.host.store import JobStore
from texllm.schemas import Job

logger = logging.getLogger(__name__)


def _default_store() -> JobStore:
    # Imported at call time so tests can swap texllm.host.app.store freely.
    from texllm.host import app as app_mod

    return app_mod.store


class ChannelService:
    def __init__(
        self,
        settings: Optional[Settings] = None,
        adapters: Optional[Dict[str, ChannelAdapter]] = None,
        dispatch: Optional[Callable[..., Any]] = None,
        store_getter: Optional[Callable[[], JobStore]] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._adapters = (
            adapters if adapters is not None else build_adapters(self.settings)
        )
        self._dispatch = dispatch or dispatch_team_job
        self._store_getter = store_getter or _default_store

    # ----- status -----

    def status_report(self) -> Dict[str, Any]:
        return {
            "channels": [
                self._adapters[name].describe() for name in sorted(self._adapters)
            ],
            "registered": registered_names(),
            "webhook_path": "/v1/channels/{channel}/webhook",
            "default_team": self.settings.channels_default_team or None,
        }

    # ----- HTTP-facing -----

    def handle_get(self, channel: str, req: WebhookRequest) -> WebhookResponse:
        adapter = self._adapters.get(channel)
        if adapter is None:
            return WebhookResponse(404, json_body={"detail": "channel not configured"})
        return adapter.handle_get(req)

    def handle_post(self, channel: str, req: WebhookRequest) -> WebhookResponse:
        adapter = self._adapters.get(channel)
        if adapter is None:
            return WebhookResponse(404, json_body={"detail": "channel not configured"})
        try:
            messages = adapter.verify_and_parse(req)
        except ChannelVerifyError:
            logger.warning("channel %s: webhook verification failed", channel)
            return WebhookResponse(401, json_body={"detail": "verification failed"})

        replies = self.handle_inbound(channel, messages)

        real = [r for r in replies if r]
        if adapter.supports_sync_reply and real:
            return WebhookResponse(200, json_body={"text": "\n\n".join(real)})
        self._send_replies(channel, adapter, messages, replies)
        return WebhookResponse(200, json_body={"ok": True, "received": len(messages)})

    def deliver(self, channel: str, messages: List[InboundMessage]) -> None:
        """Process already-verified messages and send replies out-of-band.
        Used by non-HTTP transports (the Telegram long-poll worker)."""
        adapter = self._adapters.get(channel)
        replies = self.handle_inbound(channel, messages)
        self._send_replies(channel, adapter, messages, replies)

    def adapter(self, name: str) -> Optional[ChannelAdapter]:
        return self._adapters.get(name)

    def _send_replies(
        self,
        channel: str,
        adapter: Optional[ChannelAdapter],
        messages: List[InboundMessage],
        replies: List[str],
    ) -> None:
        if adapter is None:
            return
        for msg, reply in zip(messages, replies):
            if not reply:
                continue
            try:
                adapter.send(msg.chat_ref, reply)
            except Exception:  # noqa: BLE001 — an ack send failure is not fatal
                logger.warning("channel %s: reply send failed", channel, exc_info=True)

    # ----- transport-agnostic core (poller calls this directly) -----

    def handle_inbound(
        self, channel: str, messages: List[InboundMessage]
    ) -> List[str]:
        """Process verified messages; returns reply texts ('' = say nothing)."""
        adapter = self._adapters.get(channel)
        replies: List[str] = []
        for msg in messages or []:
            msg.channel = channel
            if adapter is None or not adapter.is_allowed(msg):
                logger.info(
                    "channel %s: sender not allowlisted — dropped silently", channel
                )
                replies.append("")
                continue
            try:
                cmd = parse_command(msg.text)
            except CommandError as exc:
                replies.append(self._clip(str(exc)))
                continue
            try:
                replies.append(self._clip(self._execute(channel, msg, cmd)))
            except Exception as exc:  # noqa: BLE001 — reply the error, keep serving
                logger.warning("channel %s: command failed", channel, exc_info=True)
                replies.append(self._clip(f"error: {exc}"))
        return replies

    # ----- verbs -----

    def _execute(self, channel: str, msg: InboundMessage, cmd: ParsedCommand) -> str:
        if cmd.kind == "help":
            return HELP_TEXT
        if cmd.kind == "teams":
            return self._teams_text()
        if cmd.kind == "jobs":
            return self._jobs_text()
        if cmd.kind == "status":
            return self._status_text(cmd.arg)
        if cmd.kind == "freeform":
            default_team = (self.settings.channels_default_team or "").strip()
            if not default_team or not cmd.goal:
                return HELP_TEXT
            return self._run(channel, msg, default_team, cmd.goal, code=False)
        return self._run(channel, msg, cmd.team, cmd.goal, code=cmd.code)

    def _run(
        self, channel: str, msg: InboundMessage, team_slug: str, goal: str, *, code: bool
    ) -> str:
        from texllm.workspace import get_workspace

        if not get_workspace().get_team(team_slug):
            return f"unknown team: {team_slug} — try: teams"
        mode = "code" if code else "chat"
        try:
            _, job = self._dispatch(
                team_slug,
                goal,
                store=self._store_getter(),
                mode=mode,
                on_done=partial(self._push_completion, channel, msg.chat_ref, team_slug),
            )
        except KeyError:
            return f"unknown team: {team_slug} — try: teams"
        return (
            f"Queued {mode} run on {team_slug} — job {job.id[:8]}\n"
            f"check: status {job.id[:8]}"
        )

    def _teams_text(self) -> str:
        from texllm.workspace import get_workspace

        teams = get_workspace().list_teams()
        if not teams:
            return "no teams in the workspace yet"
        return "\n".join(f"{t['slug']} — {t['name']}" for t in teams)

    def _jobs_text(self) -> str:
        jobs = self._store_getter().list(limit=5)
        if not jobs:
            return "no jobs yet"
        lines = []
        for j in jobs:
            goal = str(j.input.get("goal") or j.goal)[:48]
            lines.append(f"{j.id[:8]} {j.status.value:<9} {j.mode:<4} {goal}")
        return "\n".join(lines)

    def _status_text(self, prefix: str) -> str:
        matches = [j for j in self._store_getter().list(limit=200) if j.id.startswith(prefix)]
        if not matches:
            return f"no job matching {prefix}"
        if len(matches) > 1:
            return "multiple matches:\n" + "\n".join(j.id[:8] for j in matches)
        return self._completion_text(str(matches[0].input.get("team") or "?"), matches[0])

    # ----- completion push -----

    def _push_completion(
        self, channel: str, chat_ref: str, team_slug: str, job: Job
    ) -> None:
        adapter = self._adapters.get(channel)
        if adapter is None or not adapter.can_push or not chat_ref:
            logger.info(
                "channel %s: completion for job %s not pushed (no push transport)",
                channel,
                job.id[:8],
            )
            return
        adapter.send(chat_ref, self._clip(self._completion_text(team_slug, job)))

    def _completion_text(self, team_slug: str, job: Job) -> str:
        summary = (job.result.summary if job.result else "") or ""
        text = f"[{team_slug}] job {job.id[:8]} {job.status.value}: {summary[:400]}"
        output = (job.result.output if job.result else None) or {}
        if output.get("mode") == "code":
            files = output.get("files_changed") or []
            passed = bool(job.result.review_passed) if job.result else False
            text += f"\nfiles changed: {len(files)} | review passed: {passed}"
            workdir = output.get("workdir")
            if workdir:
                text += f"\nworkdir: {workdir}"
        if job.status.value == "failed" and job.error:
            text += f"\nerror: {job.error[:300]}"
        return text

    def _clip(self, text: str) -> str:
        limit = max(200, int(self.settings.channels_reply_max_chars))
        if len(text) <= limit:
            return text
        return text[: limit - 1] + "…"


# ----- module singleton (house pattern: workspace/db.py) -----

_service: Optional[ChannelService] = None
_service_lock = threading.Lock()


def get_channel_service() -> ChannelService:
    global _service
    with _service_lock:
        if _service is None:
            _service = ChannelService()
        return _service


def reset_channel_service() -> None:
    global _service
    with _service_lock:
        _service = None
