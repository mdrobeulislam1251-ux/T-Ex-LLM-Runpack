"""LLM provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str  # system | user | assistant
    content: str


class CompletionResult(BaseModel):
    content: str
    model: str = ""
    provider: str = ""
    usage_tokens: int = 0


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def complete(
        self,
        messages: List[ChatMessage],
        *,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> CompletionResult:
        raise NotImplementedError
