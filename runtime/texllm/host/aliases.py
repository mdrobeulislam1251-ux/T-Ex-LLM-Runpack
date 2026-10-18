"""Persist agent ↔ user name aliases for the console and runners."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentAliases(BaseModel):
    """How the human and the agent address each other."""

    # What the user calls the agent (display + prompts)
    agent_name: str = Field(
        default="Tex",
        description="Name the user uses when addressing the agent",
        min_length=1,
        max_length=64,
    )
    # What the agent calls the user
    user_name: str = Field(
        default="Operator",
        description="Name the agent uses when addressing the user",
        min_length=1,
        max_length=64,
    )
    # Extra nicknames the user may type for the agent
    agent_aliases: List[str] = Field(
        default_factory=list,
        description="Optional alternate names for the agent",
    )
    # Extra nicknames the agent may use for the user
    user_aliases: List[str] = Field(
        default_factory=list,
        description="Optional alternate names for the user",
    )

    def prompt_preamble(self) -> str:
        aliases_agent = ", ".join(self.agent_aliases) if self.agent_aliases else "(none)"
        aliases_user = ", ".join(self.user_aliases) if self.user_aliases else "(none)"
        return (
            f"Address the user as **{self.user_name}**. "
            f"You are **{self.agent_name}**. "
            f"User may also call you: {aliases_agent}. "
            f"You may also call the user: {aliases_user}."
        )


class AliasStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or Path(".texllm") / "aliases.json"
        self._lock = threading.Lock()
        self._cache: Optional[AgentAliases] = None

    def _ensure_parent(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def get(self) -> AgentAliases:
        with self._lock:
            if self._cache is not None:
                return self._cache
            if self.path.is_file():
                try:
                    raw = json.loads(self.path.read_text(encoding="utf-8"))
                    self._cache = AgentAliases.model_validate(raw)
                    return self._cache
                except (OSError, json.JSONDecodeError, ValueError):
                    pass
            self._cache = AgentAliases()
            return self._cache

    def set(self, data: AgentAliases) -> AgentAliases:
        with self._lock:
            cleaned = data.model_copy(
                update={
                    "agent_name": data.agent_name.strip() or "Tex",
                    "user_name": data.user_name.strip() or "Operator",
                    "agent_aliases": [a.strip() for a in data.agent_aliases if a.strip()],
                    "user_aliases": [a.strip() for a in data.user_aliases if a.strip()],
                }
            )
            self._ensure_parent()
            self.path.write_text(
                cleaned.model_dump_json(indent=2),
                encoding="utf-8",
            )
            self._cache = cleaned
            return cleaned

    def patch(self, updates: Dict[str, Any]) -> AgentAliases:
        current = self.get()
        merged = current.model_copy(update=updates)
        return self.set(merged)


# Process-wide store (path can be rebound in tests)
alias_store = AliasStore()
