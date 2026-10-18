"""Discover terminal AI / agent CLIs installed on PATH (and common install dirs)."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


# Well-known agent CLIs (name → binary candidates)
KNOWN_AGENTS: Dict[str, List[str]] = {
    "claude": ["claude"],
    "codex": ["codex"],
    "gemini": ["gemini"],
    "opencode": ["opencode"],
    "cursor-agent": ["cursor-agent", "cursor"],
    "qwen": ["qwen", "qwen-code"],
    "qoder": ["qodercli", "qoder"],
    "copilot": ["copilot", "gh-copilot"],
    "devin": ["devin"],
    "aider": ["aider"],
    "continue": ["cn", "continue"],
}


@dataclass
class DetectedAgent:
    id: str
    binary: str
    path: str
    version: Optional[str] = None
    noninteractive: bool = False
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _extra_path_dirs() -> List[Path]:
    home = Path.home()
    candidates = [
        home / ".local" / "bin",
        home / ".npm-global" / "bin",
        home / "n" / "bin",
        home / ".nvm" / "current" / "bin",
        home / ".fnm" / "current" / "bin",
        home / ".cargo" / "bin",
        Path("/usr/local/bin"),
        Path("/opt/homebrew/bin"),
        Path("/home/linuxbrew/.linuxbrew/bin"),
    ]
    # Expand nvm versions if present
    nvm = home / ".nvm" / "versions" / "node"
    if nvm.is_dir():
        for child in sorted(nvm.iterdir(), reverse=True)[:5]:
            candidates.append(child / "bin")
    return [p for p in candidates if p.is_dir()]


def which_extended(name: str) -> Optional[str]:
    found = shutil.which(name)
    if found:
        return found
    for d in _extra_path_dirs():
        candidate = d / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _try_version(path: str) -> Optional[str]:
    for args in ([path, "--version"], [path, "version"], [path, "-V"]):
        try:
            proc = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
            )
            out = (proc.stdout or proc.stderr or "").strip().splitlines()
            if out:
                return out[0][:120]
        except (OSError, subprocess.TimeoutExpired):
            continue
    return None


# CLIs known to support a reasonable non-interactive prompt path
NONINTERACTIVE: Dict[str, bool] = {
    "claude": True,  # claude -p
    "codex": True,  # codex exec / -q varies by version
    "gemini": True,
    "aider": True,
    "opencode": False,
    "cursor-agent": False,
    "qwen": True,
    "qoder": False,
    "copilot": False,
    "devin": False,
    "continue": False,
}


def detect_agents() -> List[DetectedAgent]:
    found: List[DetectedAgent] = []
    seen_paths: set[str] = set()

    for agent_id, binaries in KNOWN_AGENTS.items():
        for bin_name in binaries:
            path = which_extended(bin_name)
            if not path or path in seen_paths:
                continue
            seen_paths.add(path)
            version = _try_version(path)
            ni = NONINTERACTIVE.get(agent_id, False)
            notes = (
                "Supports non-interactive spawn from host"
                if ni
                else "Detected on PATH; interactive TUI use recommended (host spawn may be limited)"
            )
            found.append(
                DetectedAgent(
                    id=agent_id,
                    binary=bin_name,
                    path=path,
                    version=version,
                    noninteractive=ni,
                    notes=notes,
                )
            )
            break  # one binary per agent id

    return found


def detect_report() -> Dict[str, Any]:
    agents = detect_agents()
    return {
        "count": len(agents),
        "agents": [a.to_dict() for a in agents],
        "path_scanned": True,
        "execution_modes": [
            {
                "id": "local_cli",
                "description": "Spawn an installed terminal agent CLI (no API key required if that CLI is already authenticated)",
            },
            {
                "id": "openai_compat",
                "description": "Call OpenAI-compatible HTTP APIs via LLM_API_KEY / LLM_BASE_URL",
            },
            {
                "id": "mock",
                "description": "Offline deterministic mock for demos and CI",
            },
            {
                "id": "team_runner",
                "description": "Built-in multi-role runner (uses mock or API provider)",
            },
        ],
    }
