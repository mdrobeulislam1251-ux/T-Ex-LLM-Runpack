"""Provider factory: user API key / Claude CLI wins; mock only as last resort."""

from __future__ import annotations

import logging
import os

from texllm.config import Settings, get_settings
from texllm.providers.anthropic import AnthropicProvider
from texllm.providers.base import LLMProvider
from texllm.providers.claude_cli import ClaudeCLIProvider
from texllm.providers.mock import MockProvider
from texllm.providers.openai_compat import OpenAICompatProvider

logger = logging.getLogger(__name__)

# Sensible defaults per vendor (OpenAI-compatible unless Anthropic)
DEFAULT_BASE = {
    "openai": "https://api.openai.com/v1",
    "xai": "https://api.x.ai/v1",
    "grok": "https://api.x.ai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "anthropic": "https://api.anthropic.com",
    "claude": "https://api.anthropic.com",
    "custom": "https://api.openai.com/v1",
}

DEFAULT_MODEL = {
    "openai": "gpt-4o-mini",
    "xai": "grok-3",
    "grok": "grok-3",
    "gemini": "gemini-2.0-flash",
    "anthropic": "claude-sonnet-4-20250514",
    "claude": "claude-sonnet-4-20250514",
}


def get_provider(settings: Settings | None = None) -> LLMProvider:
    """
    Resolution order (product-usable):
    1. Saved auth profile with API key / setup-token / working Claude CLI
    2. Env LLM_API_KEY
    3. Mock (offline draft only)
    """
    settings = settings or get_settings()

    # CI-only: TEXLLM_FORCE_MOCK=1
    if os.environ.get("TEXLLM_FORCE_MOCK", "").strip() in ("1", "true", "yes"):
        return MockProvider()

    try:
        from texllm.host.credentials import resolve_runtime

        rt = resolve_runtime()
    except Exception as exc:  # noqa: BLE001
        logger.debug("resolve_runtime: %s", exc)
        rt = {"method": "mock", "source": "fallback"}

    method = (rt.get("method") or "").strip()
    key = (rt.get("api_key") or "").strip()
    provider = (rt.get("provider") or "").strip().lower()
    model = (rt.get("model") or settings.llm_model or "").strip()
    base = (rt.get("base_url") or "").strip()
    timeout = int(getattr(settings, "local_cli_timeout_sec", 180) or 180)
    cwd = str(getattr(settings, "local_cli_cwd", ".") or ".")

    # --- API key profiles (Grok, OpenAI, Gemini, Anthropic, custom) ---
    if method == "api_key" and key:
        return _from_api_key(provider, key, base, model)

    # --- Claude Max setup-token ---
    if method == "setup_token" and key:
        try:
            return ClaudeCLIProvider(
                setup_token=key, timeout_sec=timeout, cwd=cwd
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("setup-token CLI failed, try Anthropic API headers: %s", exc)
            return AnthropicProvider(
                api_key=key,
                default_model=model or DEFAULT_MODEL["anthropic"],
            )

    # --- Local Claude CLI only if binary exists (skip broken profiles) ---
    if method == "local_cli":
        agent_id = (rt.get("agent_id") or "claude").strip()
        if agent_id == "claude":
            try:
                return ClaudeCLIProvider(timeout_sec=timeout, cwd=cwd)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Claude CLI profile set but unusable (%s) — falling back",
                    exc,
                )
        else:
            logger.warning(
                "local_cli agent_id=%s not supported; use API key for Grok/OpenAI/Gemini",
                agent_id,
            )

    # --- Environment LLM_* ---
    if settings.llm_api_key and settings.llm_api_key.strip():
        k = settings.llm_api_key.strip()
        b = settings.llm_base_url or DEFAULT_BASE["openai"]
        m = settings.llm_model or DEFAULT_MODEL["openai"]
        if k.startswith("sk-ant-") or "anthropic.com" in b:
            return AnthropicProvider(api_key=k, default_model=m, base_url=b)
        return OpenAICompatProvider(base_url=b, api_key=k, default_model=m)

    # Explicit mock env
    if (settings.llm_provider or "").strip().lower() == "mock":
        return MockProvider()

    logger.info("No API key / working CLI — MockProvider (offline drafts)")
    return MockProvider()


def _from_api_key(
    provider: str, key: str, base: str, model: str
) -> LLMProvider:
    prov = provider or "openai"
    if prov in ("anthropic", "claude"):
        return AnthropicProvider(
            api_key=key,
            default_model=model or DEFAULT_MODEL["anthropic"],
            base_url=base or DEFAULT_BASE["anthropic"],
        )
    # Grok / OpenAI / Gemini OpenAI-compat / custom
    b = base or DEFAULT_BASE.get(prov, DEFAULT_BASE["openai"])
    m = model or DEFAULT_MODEL.get(prov, DEFAULT_MODEL["openai"])
    return OpenAICompatProvider(base_url=b, api_key=key, default_model=m)


def describe_active_provider() -> dict:
    """Human-readable status for the UI."""
    try:
        p = get_provider()
        from texllm.host.credentials import resolve_runtime

        rt = resolve_runtime()
        return {
            "name": getattr(p, "name", type(p).__name__),
            "method": rt.get("method"),
            "provider": rt.get("provider"),
            "profile_id": rt.get("profile_id"),
            "has_secret": bool(rt.get("api_key")),
            "source": rt.get("source"),
            "usable": p.name != "mock" or rt.get("method") == "mock",
            "hint": _hint(rt, p.name),
        }
    except Exception as exc:  # noqa: BLE001
        return {"name": "error", "hint": str(exc), "usable": False}


def _hint(rt: dict, name: str) -> str:
    if name == "mock":
        return (
            "No working AI connected. Paste a Grok/OpenAI/Claude/Gemini API key "
            "and click Save. (Grok = xAI API key, not a local CLI.)"
        )
    if rt.get("method") == "local_cli":
        return "Using Claude Code CLI on this machine."
    if rt.get("method") == "api_key":
        return f"Using API key profile ({rt.get('provider')})."
    return f"Provider: {name}"
