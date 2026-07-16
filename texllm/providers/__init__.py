"""Provider factory."""

from __future__ import annotations

from texllm.config import Settings, get_settings
from texllm.providers.base import LLMProvider
from texllm.providers.mock import MockProvider
from texllm.providers.openai_compat import OpenAICompatProvider


def get_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
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
