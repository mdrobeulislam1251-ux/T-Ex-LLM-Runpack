"""ChannelService — allowlist gate, command routing, ack + completion push.

Uses a FakeAdapter capturing sends and the REAL dispatch pipeline (mock LLM
provider), so this is the end-to-end chat → run → push loop, offline.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import List, Optional

import pytest

os.environ["TEXLLM_FORCE_MOCK"] = "1"
os.environ["LLM_PROVIDER"] = "mock"

from texllm import config as config_mod
from texllm.channels.base import ChannelAdapter, InboundMessage, WebhookRequest
from texllm.channels.service import ChannelService
from texllm.host.store import JobStore
from texllm.schemas import Job, JobResult, JobStatus


class FakeAdapter(ChannelAdapter):
    name = "fake"

    def __init__(self, allowed=frozenset({"42"}), sync_reply=False, send_raises=False):
        self._allowed = allowed
        self.sent: List[tuple] = []
        self.push_attempts = 0
        self.send_raises = send_raises
        # ClassVar override per-instance for test convenience
        self.__class__.supports_sync_reply = sync_reply

    @classmethod
    def from_settings(cls, settings) -> Optional["FakeAdapter"]:
        return None

    def verify_and_parse(self, req: WebhookRequest):
        import json

        payload = json.loads(req.body.decode("utf-8"))
        return [
            InboundMessage(
                sender_id=payload["sender"], chat_ref=payload["chat"], text=payload["text"]
            )
        ]

    def send(self, chat_ref: str, text: str) -> None:
        self.push_attempts += 1
        if self.send_raises:
            raise RuntimeError("push transport down")
        self.sent.append((chat_ref, text))


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.chdir(tmp_path)
    config_mod.get_settings.cache_clear()
    from texllm.workspace import db as db_mod

    db_mod._workspace = None  # type: ignore[attr-defined]
    FakeAdapter.supports_sync_reply = False
    yield
    db_mod._workspace = None  # type: ignore[attr-defined]
    config_mod.get_settings.cache_clear()


def _service(fa: FakeAdapter, store: JobStore, **settings_overrides) -> ChannelService:
    settings = config_mod.Settings(_env_file=None, **settings_overrides)
    return ChannelService(
        settings=settings, adapters={"fake": fa}, store_getter=lambda: store
    )


def _msg(text: str, sender="42", chat="chat-1") -> InboundMessage:
    return InboundMessage(sender_id=sender, chat_ref=chat, text=text)


def _wait(cond, tries=200, delay=0.05):
    for _ in range(tries):
        if cond():
            return True
        time.sleep(delay)
    return False


def test_allowlisted_run_acks_and_pushes_completion():
    fa = FakeAdapter()
    store = JobStore()
    svc = _service(fa, store)

    replies = svc.handle_inbound("fake", [_msg("run dev Ship the notes")])
    assert len(replies) == 1
    assert "Queued chat run on dev" in replies[0]
    assert "status " in replies[0]

    jobs = store.list()
    assert len(jobs) == 1
    assert _wait(lambda: store.get(jobs[0].id).status == JobStatus.succeeded)
    assert _wait(lambda: len(fa.sent) == 1)
    chat_ref, text = fa.sent[0]
    assert chat_ref == "chat-1"
    assert "[dev]" in text and "succeeded" in text


def test_denied_and_empty_allowlist_silent():
    store = JobStore()

    fa = FakeAdapter(allowed=frozenset({"42"}))
    svc = _service(fa, store)
    replies = svc.handle_inbound("fake", [_msg("run dev x", sender="999")])
    assert replies == [""]

    fa2 = FakeAdapter(allowed=frozenset())
    svc2 = _service(fa2, store)
    replies2 = svc2.handle_inbound("fake", [_msg("run dev x")])
    assert replies2 == [""]

    assert store.list() == []
    assert fa.sent == [] and fa2.sent == []


def test_freeform_routes_to_default_team():
    fa = FakeAdapter()
    store = JobStore()
    svc = _service(fa, store, channels_default_team="dev")
    replies = svc.handle_inbound("fake", [_msg("what should we build next?")])
    assert "Queued chat run on dev" in replies[0]
    assert len(store.list()) == 1
    # Drain the dispatch thread (completion push is its last act) so it never
    # crosses into the next test: WorkspaceDB paths are CWD-relative.
    assert _wait(lambda: len(fa.sent) == 1)


def test_freeform_without_default_team_is_help():
    fa = FakeAdapter()
    store = JobStore()
    svc = _service(fa, store)
    replies = svc.handle_inbound("fake", [_msg("hello there")])
    assert "run <team>" in replies[0]
    assert store.list() == []


def test_teams_jobs_status_and_unknown_team():
    fa = FakeAdapter()
    store = JobStore()
    svc = _service(fa, store)

    teams_reply = svc.handle_inbound("fake", [_msg("teams")])[0]
    assert "dev" in teams_reply

    assert "unknown team" in svc.handle_inbound("fake", [_msg("run nosuch do x")])[0]

    ack = svc.handle_inbound("fake", [_msg("run dev Draft notes")])[0]
    job_id8 = ack.split("job ")[1][:8]
    _wait(lambda: store.list() and store.list()[0].status == JobStatus.succeeded)

    jobs_reply = svc.handle_inbound("fake", [_msg("jobs")])[0]
    assert job_id8 in jobs_reply

    status_reply = svc.handle_inbound("fake", [_msg(f"status {job_id8}")])[0]
    assert "succeeded" in status_reply

    assert "no job matching" in svc.handle_inbound("fake", [_msg("status zzzzzzz")])[0]

    assert _wait(lambda: len(fa.sent) == 1)  # drain the dispatch thread


def test_code_completion_mentions_files_changed():
    fa = FakeAdapter()
    store = JobStore()

    def fake_dispatch(team_slug, goal, *, store, mode="chat", workdir=None, on_done=None, **kw):
        job = Job(
            firmware_id="x",
            firmware_version="0.1.0",
            goal=goal,
            mode=mode,
            status=JobStatus.succeeded,
            result=JobResult(
                summary="Added healthz",
                output={"mode": "code", "files_changed": ["a.py", "b.py"], "workdir": "/w"},
                review_passed=True,
            ),
        )
        store.put(job)
        if on_done:
            on_done(job)
        return {"id": "t", "slug": team_slug}, job

    settings = config_mod.Settings(_env_file=None)
    svc = ChannelService(
        settings=settings,
        adapters={"fake": fa},
        dispatch=fake_dispatch,
        store_getter=lambda: store,
    )
    ack = svc.handle_inbound("fake", [_msg("run dev --code add healthz")])[0]
    assert "Queued code run" in ack
    assert len(fa.sent) == 1
    completion = fa.sent[0][1]
    assert "files changed: 2" in completion
    assert "review passed: True" in completion


def test_sync_reply_adapter_gets_ack_in_response():
    fa = FakeAdapter(sync_reply=True)
    store = JobStore()
    svc = _service(fa, store)
    resp = svc.handle_post(
        "fake",
        WebhookRequest(body=b'{"sender": "42", "chat": "c", "text": "teams"}'),
    )
    assert resp.status_code == 200
    assert resp.json_body and "dev" in resp.json_body["text"]
    assert fa.sent == []  # ack rode the response, not send()


def test_push_failure_never_corrupts_job():
    fa = FakeAdapter(send_raises=True)
    store = JobStore()
    svc = _service(fa, store)
    svc.handle_inbound("fake", [_msg("run dev Draft notes")])
    jobs = store.list()
    assert _wait(lambda: store.get(jobs[0].id).status == JobStatus.succeeded)
    assert _wait(lambda: fa.push_attempts == 1)  # drain the dispatch thread


def test_unconfigured_channel_404_and_bad_sig_401():
    from texllm.channels.base import ChannelVerifyError

    class RejectingAdapter(FakeAdapter):
        name = "rej"

        def verify_and_parse(self, req):
            raise ChannelVerifyError("nope")

    store = JobStore()
    svc = ChannelService(
        settings=config_mod.Settings(_env_file=None),
        adapters={"rej": RejectingAdapter()},
        store_getter=lambda: store,
    )
    assert svc.handle_post("ghost", WebhookRequest(body=b"{}")).status_code == 404
    resp = svc.handle_post("rej", WebhookRequest(body=b"{}"))
    assert resp.status_code == 401
    assert "nope" not in (resp.json_body or {}).get("detail", "")  # generic detail only
