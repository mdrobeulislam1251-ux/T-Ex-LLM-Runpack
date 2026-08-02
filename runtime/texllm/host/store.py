"""In-memory job store (MVP)."""

from __future__ import annotations

import threading
from typing import Dict, List, Optional

from texllm.schemas import Job


class JobStore:
    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def put(self, job: Job) -> Job:
        with self._lock:
            self._jobs[job.id] = job
            return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self, limit: int = 50) -> List[Job]:
        with self._lock:
            jobs = sorted(
                self._jobs.values(),
                key=lambda j: j.created_at,
                reverse=True,
            )
            return jobs[:limit]
