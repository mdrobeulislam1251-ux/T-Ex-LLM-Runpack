"""Provider factory — env LLM_* or default auth profile (NanoClaw-style)."""

from __future__ import annotations

from texllm.config import Settings, get_settings
from texllm.providers.anthropic import AnthropicProvider
from texllm.providers.base import LLMProvider
from texllm.providers.mock import MockProvider
from texllm.providers.openai_compat import OpenAICompatProvider


def get_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()

    # Prefer stored auth profile when present (subscription token or API key)
    try:
        from texllm.host.credentials import resolve_runtime

        rt = resolve_runtime()
    except Exception:
        rt = {"method": "mock", "source": "fallback"}

    method = rt.get("method")
    if method == "local_cli":
        # Runner should spawn CLI; mock as fallback if complete() is called
        return MockProvider()

    if method in ("api_key", "setup_token", "oauth_codex", "oauth_google") and rt.get(
        "api_key"
    ):
        provider = rt.get("provider") or "openai"
        model = rt.get("model") or settings.llm_model
        base = rt.get("base_url") or settings.llm_base_url
        key = rt["api_key"]
        extra = rt.get("extra_headers") or {}

        if provider == "anthropic" or method == "setup_token":
            return AnthropicProvider(
                api_key=key,
                default_model=model or "claude-sonnet-4-20250514",
                base_url=base if "anthropic" in base else "https://api.anthropic.com",
                extra_headers=extra,
            )
        # OpenAI / xAI / Gemini OpenAI-compat gateways / Codex token as bearer
        return OpenAICompatProvider(
            base_url=base,
            api_key=key,
            default_model=model or "gpt-4o-mini",
        )

    # Env-driven
    kind = settings.resolve_provider()
    if kind == "mock":
        return MockProvider()
    if kind == "openai":
        if not settings.llm_api_key:
            raise ValueError("LLM_API_KEY required when LLM_PROVIDER=openai")
        return OpenAICompatProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            default_model=settings.llm_model,
        )
    raise ValueError(f"Unknown LLM_PROVIDER: {kind}")
