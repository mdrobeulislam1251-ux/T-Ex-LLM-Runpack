"""Claude-first provider factory: setup-token / API key / local CLI / mock."""

from __future__ import annotations

import logging

from texllm.config import Settings, get_settings
from texllm.providers.anthropic import AnthropicProvider
from texllm.providers.base import LLMProvider
from texllm.providers.claude_cli import ClaudeCLIProvider
from texllm.providers.mock import MockProvider
from texllm.providers.openai_compat import OpenAICompatProvider

logger = logging.getLogger(__name__)


def get_provider(settings: Settings | None = None) -> LLMProvider:
    """
    Claude-first resolution order:
    1. Default auth profile (setup_token | local_cli | anthropic api_key)
    2. Env LLM_* if set
    3. Mock (offline demo only)
    """
    settings = settings or get_settings()

    # Explicit mock always wins (CI / offline demos)
    if (settings.llm_provider or "").strip().lower() == "mock":
        return MockProvider()

    try:
        from texllm.host.credentials import resolve_runtime

        rt = resolve_runtime()
    except Exception as exc:  # noqa: BLE001
        logger.debug("resolve_runtime failed: %s", exc)
        rt = {}

    method = (rt.get("method") or "").strip()
    key = (rt.get("api_key") or "").strip()
    provider = (rt.get("provider") or "").strip()
    model = (rt.get("model") or settings.llm_model or "").strip()
    timeout = int(getattr(settings, "local_cli_timeout_sec", 180) or 180)
    cwd = str(getattr(settings, "local_cli_cwd", ".") or ".")

    # --- Claude setup-token (Max/Pro): prefer CLI with token inject ---
    if method == "setup_token" and key:
        try:
            return ClaudeCLIProvider(
                setup_token=key, timeout_sec=timeout, cwd=cwd
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Claude CLI unavailable for setup-token, try API: %s", exc)
            return AnthropicProvider(
                api_key=key,
                default_model=model or "claude-sonnet-4-20250514",
                base_url="https://api.anthropic.com",
            )

    # --- Local Claude CLI session ---
    if method == "local_cli":
        agent_id = (rt.get("agent_id") or "claude").strip()
        if agent_id == "claude":
            return ClaudeCLIProvider(timeout_sec=timeout, cwd=cwd)
        # non-Claude CLIs not in Claude-first slice — mock with clear error on use
        logger.warning("local_cli agent_id=%s ignored in Claude-first mode", agent_id)

    # --- Anthropic API key ---
    if method == "api_key" and provider in ("anthropic", "claude") and key:
        return AnthropicProvider(
            api_key=key,
            default_model=model or "claude-sonnet-4-20250514",
            base_url="https://api.anthropic.com",
        )

    # --- Other stored profiles (non-Claude) — only if explicitly default ---
    if method in ("api_key", "oauth_codex", "oauth_google") and key:
        base = rt.get("base_url") or settings.llm_base_url
        if provider == "anthropic":
            return AnthropicProvider(
                api_key=key,
                default_model=model or "claude-sonnet-4-20250514",
            )
        return OpenAICompatProvider(
            base_url=base,
            api_key=key,
            default_model=model or settings.llm_model,
        )

    # --- Env fallback (Claude-oriented if key looks Anthropic) ---
    kind = settings.resolve_provider()
    if kind == "openai" and settings.llm_api_key:
        k = settings.llm_api_key.strip()
        if k.startswith("sk-ant-") or "anthropic" in (settings.llm_base_url or ""):
            return AnthropicProvider(
                api_key=k,
                default_model=settings.llm_model or "claude-sonnet-4-20250514",
            )
        return OpenAICompatProvider(
            base_url=settings.llm_base_url,
            api_key=k,
            default_model=settings.llm_model,
        )

    if kind == "mock":
        return MockProvider()

    # Last resort: mock so host still boots; jobs will be demo-quality
    logger.warning("No Claude profile/API key — using mock provider")
    return MockProvider()
