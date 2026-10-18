"""Spawn a local terminal agent CLI with a prompt (backend subprocess)."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional

from texllm.agents.detect import DetectedAgent, detect_agents


class LocalCliError(RuntimeError):
    pass


def _build_argv(agent: DetectedAgent, prompt: str) -> List[str]:
    """Best-effort non-interactive argv per known CLI family."""
    path = agent.path
    aid = agent.id

    if aid == "claude":
        # Claude Code print mode (auth via local CLI login, not our API key)
        return [
            path,
            "-p",
            prompt,
            "--output-format",
            "text",
            "--permission-mode",
            "bypassPermissions",
        ]
    if aid == "codex":
        # Codex CLI: try exec-style; versions differ
        if shutil.which(path):
            return [path, "exec", "--full-auto", prompt]
        return [path, prompt]
    if aid == "gemini":
        return [path, "-p", prompt]
    if aid == "aider":
        return [path, "--yes", "--message", prompt]
    if aid == "qwen":
        return [path, "-p", prompt]
    # Generic: pass prompt as last arg (may fail — surface stderr)
    return [path, prompt]


def run_local_agent(
    agent_id: str,
    prompt: str,
    *,
    cwd: Optional[str] = None,
    timeout_sec: int = 180,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    agents = {a.id: a for a in detect_agents()}
    agent = agents.get(agent_id)
    if not agent:
        raise LocalCliError(
            f"Agent '{agent_id}' not found on PATH. Install it or pick another. "
            f"Detected: {list(agents.keys()) or 'none'}"
        )

    argv = _build_argv(agent, prompt)
    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    started = time.time()
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd=cwd or os.getcwd(),
            env=run_env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise LocalCliError(
            f"Agent '{agent_id}' timed out after {timeout_sec}s"
        ) from exc
    except OSError as exc:
        raise LocalCliError(f"Failed to spawn {agent.path}: {exc}") from exc

    duration = round(time.time() - started, 3)
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()

    return {
        "agent_id": agent_id,
        "binary": agent.binary,
        "path": agent.path,
        "argv": argv[:-1] + ["<prompt>"],  # don't echo full prompt in logs
        "exit_code": proc.returncode,
        "duration_sec": duration,
        "stdout": stdout[-50000:],
        "stderr": stderr[-10000:],
        "ok": proc.returncode == 0 and bool(stdout),
        "auth_note": (
            "This path uses the CLI's own login/credentials "
            "(e.g. `claude auth login`), not T-ex LLM_API_KEY."
        ),
    }
