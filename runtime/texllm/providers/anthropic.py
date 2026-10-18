"""Anthropic Messages API (console API keys sk-ant-…)."""

from __future__ import annotations

from typing import Dict, List, Optional

import httpx

from texllm.providers.base import ChatMessage, CompletionResult, LLMProvider


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(
        self,
        api_key: str,
        default_model: str = "claude-sonnet-4-20250514",
        base_url: str = "https://api.anthropic.com",
        extra_headers: Optional[Dict[str, str]] = None,
        timeout: float = 120.0,
    ) -> None:
        self.api_key = api_key
        self.default_model = default_model
        self.base_url = base_url.rstrip("/")
        self.extra_headers = extra_headers or {}
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
        system_parts = [m.content for m in messages if m.role == "system"]
        chat = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        ]
        if not chat:
            chat = [{"role": "user", "content": "Hello"}]
        if chat[0]["role"] != "user":
            chat.insert(0, {"role": "user", "content": "(continue)"})

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            **self.extra_headers,
        }
        body: Dict = {
            "model": use_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": chat,
        }
        if system_parts:
            body["system"] = "\n\n".join(system_parts)

        url = f"{self.base_url}/v1/messages"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=headers, json=body)
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"Anthropic API {resp.status_code}: {resp.text[:500]}"
                )
            data = resp.json()

        content_blocks = data.get("content") or []
        text = ""
        for block in content_blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                text += block.get("text") or ""
        usage = data.get("usage") or {}
        tokens = int(usage.get("input_tokens") or 0) + int(
            usage.get("output_tokens") or 0
        )
        return CompletionResult(
            content=text,
            model=data.get("model") or use_model,
            provider=self.name,
            usage_tokens=tokens,
        )
