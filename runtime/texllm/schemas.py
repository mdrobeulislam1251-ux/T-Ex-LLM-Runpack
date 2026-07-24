"""Shared job / handoff schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class RoleName(str, Enum):
    planner = "planner"
    executor = "executor"
    reviewer = "reviewer"
    integrator = "integrator"


class Handoff(BaseModel):
    """Explicit message between worker roles."""

    from_role: RoleName
    to_role: Optional[RoleName] = None
    content: str
    data: Dict[str, Any] = Field(default_factory=dict)
    ts: datetime = Field(default_factory=utcnow)


class Artifact(BaseModel):
    name: str
    kind: str = "text"
    content: Any


class JobCreate(BaseModel):
    firmware_id: str = "sample-assistant"
    firmware_version: str = "0.1.0"
    input: Dict[str, Any] = Field(default_factory=dict)
    goal: str = ""


class JobResult(BaseModel):
    summary: str = ""
    output: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[Artifact] = Field(default_factory=list)
    review_passed: bool = False
    iterations: int = 0
    handoffs: List[Handoff] = Field(default_factory=list)


class Job(BaseModel):
    id: str = Field(default_factory=new_id)
    firmware_id: str
    firmware_version: str
    goal: str
    input: Dict[str, Any] = Field(default_factory=dict)
    status: JobStatus = JobStatus.queued
    result: Optional[JobResult] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    def touch(self) -> None:
        self.updated_at = utcnow()
