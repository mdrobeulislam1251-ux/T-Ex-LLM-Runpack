"""Claude via local `claude` CLI (login session or CLAUDE_CODE_OAUTH_TOKEN)."""

from __future__ import annotations

import os
import shutil
from typing import Dict, List, Optional

from texllm.agents.detect import which_extended
from texllm.agents.local_cli import LocalCliError, run_local_agent
from texllm.providers.base import ChatMessage, CompletionResult, LLMProvider


def _find_claude() -> Optional[str]:
    return which_extended("claude")


class ClaudeCLIProvider(LLMProvider):
    """
    NanoClaw-style: use Claude Code on the host.

    - session: user ran `claude auth login`
    - setup_token: inject CLAUDE_CODE_OAUTH_TOKEN for this process only
    """

    name = "claude_cli"

    def __init__(
        self,
        *,
        setup_token: str = "",
        timeout_sec: int = 180,
        cwd: Optional[str] = None,
    ) -> None:
        self.setup_token = (setup_token or "").strip()
        self.timeout_sec = timeout_sec
        self.cwd = cwd or os.getcwd()
        path = _find_claude()
        if not path:
            raise ValueError(
                "claude CLI not found on PATH. Install Claude Code and retry."
            )
        self.claude_path = path

    def complete(
        self,
        messages: List[ChatMessage],
        *,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> CompletionResult:
        prompt = _messages_to_prompt(messages)
        env: Dict[str, str] = {}
        if self.setup_token:
            env["CLAUDE_CODE_OAUTH_TOKEN"] = self.setup_token
            # Some builds also accept this
            env["ANTHROPIC_AUTH_TOKEN"] = self.setup_token

        # Prefer direct argv using known path (run_local_agent re-detects by id)
        try:
            result = run_local_agent(
                "claude",
                prompt,
                cwd=self.cwd,
                timeout_sec=self.timeout_sec,
                env=env or None,
            )
        except LocalCliError as exc:
            raise RuntimeError(str(exc)) from exc

        if not result.get("ok") and not result.get("stdout"):
            err = result.get("stderr") or f"exit {result.get('exit_code')}"
            raise RuntimeError(f"claude CLI failed: {err}")

        text = (result.get("stdout") or "").strip()
        if not text and result.get("stderr"):
            # some builds print to stderr
            text = str(result.get("stderr")).strip()

        return CompletionResult(
            content=text,
            model=model or "claude-cli",
            provider=self.name,
            usage_tokens=max(1, len(text) // 4),
        )


def _messages_to_prompt(messages: List[ChatMessage]) -> str:
    parts: List[str] = []
    for m in messages:
        role = m.role.upper()
        parts.append(f"[{role}]\n{m.content}")
    parts.append(
        "\n[INSTRUCTION]\nRespond as the assistant. "
        "If JSON was requested, return JSON only."
    )
    return "\n\n".join(parts)
