"""Shared job state for team runners."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from texllm.schemas import Artifact, Handoff


class TeamState(BaseModel):
    goal: str
    input: Dict[str, Any] = Field(default_factory=dict)
    plan: Optional[Dict[str, Any]] = None
    draft: str = ""
    review: Optional[Dict[str, Any]] = None
    final: Optional[Dict[str, Any]] = None
    handoffs: List[Handoff] = Field(default_factory=list)
    artifacts: List[Artifact] = Field(default_factory=list)
    tool_log: List[Dict[str, Any]] = Field(default_factory=list)
    iteration: int = 0
    review_retries: int = 0
    tokens_used: int = 0

    def add_handoff(self, handoff: Handoff) -> None:
        self.handoffs.append(handoff)
