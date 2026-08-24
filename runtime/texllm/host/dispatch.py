"""Queue-and-run helper shared by POST /v1/workspace/teams/{slug}/run-async
and the messaging channels service — one dispatch code path, two front doors.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Dict, Optional, Tuple

from texllm.host.store import JobStore
from texllm.schemas import Job
from texllm.workers.runner import TeamRunner
from texllm.workspace.db import WorkspaceDB
from texllm.workspace.team_run import prepare_team_job

logger = logging.getLogger(__name__)


def dispatch_team_job(
    team_slug: str,
    goal: str,
    *,
    store: JobStore,
    mode: str = "chat",
    workdir: Optional[str] = None,
    verify: Optional[str] = None,
    db: Optional[WorkspaceDB] = None,
    runner_factory: Callable[[], TeamRunner] = TeamRunner,
    on_done: Optional[Callable[[Job], None]] = None,
) -> Tuple[Dict[str, Any], Job]:
    """Prepare a team job, queue it, and run it on a daemon thread.

    Returns (team, queued_job) immediately; raises KeyError for an unknown
    team. The thread stores the final job, logs workspace activity, then fires
    on_done(final_job). on_done exceptions are logged and swallowed — the job
    result is already persisted in the store by then.
    """
    team, job = prepare_team_job(
        team_slug, goal, db=db, mode=mode, workdir=workdir, verify=verify
    )
    store.put(job)
    team_id = team["id"]

    def _run_and_log() -> None:
        queued = store.get(job.id)
        if not queued:
            return
        updated = runner_factory().run_job(queued)
        store.put(updated)
        try:
            from texllm.workspace import get_workspace

            (db or get_workspace()).log_activity(
                team_id,
                "flow_run",
                f"Flow: {goal[:80]}",
                f"status={updated.status.value} mode={updated.mode}",
            )
        except Exception:  # noqa: BLE001 — activity log must never kill a run
            logger.debug("activity log failed for job %s", job.id)
        if on_done is not None:
            try:
                on_done(updated)
            except Exception:  # noqa: BLE001 — push failures never touch job state
                logger.warning("on_done callback failed for job %s", job.id, exc_info=True)

    threading.Thread(target=_run_and_log, daemon=True).start()
    return team, job
