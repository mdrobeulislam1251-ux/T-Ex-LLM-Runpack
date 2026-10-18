"""OpenAI-compatible chat completions (Grok, OpenAI, local, etc.)."""

from __future__ import annotations

from typing import List, Optional

import httpx

from texllm.providers.base import ChatMessage, CompletionResult, LLMProvider


class OpenAICompatProvider(LLMProvider):
    name = "openai"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        default_model: str,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model
        self.timeout = timeout

    def complete(
        self,
        messages: List[ChatMessage],
        *,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> CompletionResult:
        use_model = model or self.default_model
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": use_model,
            "messages": [m.model_dump() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]["message"]["content"] or ""
        usage = data.get("usage") or {}
        tokens = int(usage.get("total_tokens") or 0)
        return CompletionResult(
            content=choice,
            model=data.get("model") or use_model,
            provider=self.name,
            usage_tokens=tokens,
        )
