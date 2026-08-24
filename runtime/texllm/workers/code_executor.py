"""Code-mode executor: drives a headless coding agent in a per-run workdir.

This is the "real hands" for the TeamRunner. In code mode the executor role does
not draft prose — it invokes a headless Claude Code session (``claude -p`` with
file/shell tools allowed) inside a working directory, then measures what actually
changed (git diff when available, filesystem snapshot otherwise) so the reviewer
role reviews a real diff and the job result carries real artifacts.

The agent command is injectable (``run_cmd``) so tests stay offline and
deterministic — the same contract the mock LLM provider follows.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from texllm.config import Settings, get_settings

# (argv, cwd, env, timeout_sec) -> (exit_code, stdout, stderr)
RunCmd = Callable[[List[str], str, Dict[str, str], int], Tuple[int, str, str]]

_SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".texllm", "dist"}
_SCAN_CAP = 20000
_PROMPT_SECTION_CAP = 4000
_REVIEW_DIFF_CAP = 6000
_SYNTH_DIFF_FILE_CAP = 40_000


@dataclass
class CodeRunOutcome:
    ok: bool
    summary: str
    workdir: str
    files_changed: List[str] = field(default_factory=list)
    diff: str = ""
    log: str = ""


def _default_run_cmd(
    argv: List[str], cwd: str, env: Dict[str, str], timeout: int
) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout if isinstance(exc.stdout, str) else ""
        return 124, out, f"agent timed out after {timeout}s"


class CodeExecutor:
    """Runs the coding agent and reports real changes from the workdir."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        run_cmd: Optional[RunCmd] = None,
        agent_bin: Optional[str] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._run_cmd = run_cmd
        self.agent_bin = agent_bin or self.settings.code_agent_bin
        # Cumulative baseline per workdir: diffs always compare against the
        # state before the FIRST attempt, so review retries see total change.
        self._baselines: Dict[str, Any] = {}

    # ----- availability -----

    def available(self) -> bool:
        if self._run_cmd is not None:
            return True
        if shutil.which(self.agent_bin):
            return True
        try:
            from texllm.agents.detect import which_extended

            return bool(which_extended(self.agent_bin))
        except Exception:  # noqa: BLE001
            return False

    def _resolve_bin(self) -> str:
        path = shutil.which(self.agent_bin)
        if path:
            return path
        try:
            from texllm.agents.detect import which_extended

            found = which_extended(self.agent_bin)
            if found:
                return found
        except Exception:  # noqa: BLE001
            pass
        return self.agent_bin

    # ----- workdir -----

    def prepare_workdir(self, job_id: str, explicit: Optional[str] = None) -> Path:
        """Explicit workdir is used in place; otherwise an isolated per-job dir."""
        if explicit:
            path = Path(explicit)
            if not path.is_dir():
                raise ValueError(f"workdir does not exist: {explicit}")
            return path

        runs_dir = Path(self.settings.code_runs_dir)
        workdir = runs_dir / job_id
        workdir.mkdir(parents=True, exist_ok=True)
        if shutil.which("git") and not (workdir / ".git").exists():
            self._git(workdir, "init", "-q")
            self._git(
                workdir,
                "-c",
                "user.email=texllm@local",
                "-c",
                "user.name=T-Ex Runner",
                "commit",
                "--allow-empty",
                "-m",
                "texllm baseline",
                "-q",
            )
        return workdir

    # ----- execution -----

    def execute(
        self,
        *,
        goal: str,
        plan: Optional[Dict[str, Any]],
        feedback: Optional[Dict[str, Any]],
        workdir: Path,
    ) -> CodeRunOutcome:
        key = str(workdir.resolve())
        if key not in self._baselines:
            self._baselines[key] = self._snapshot(workdir)

        prompt = self._build_prompt(goal, plan, feedback)
        argv = [
            self._resolve_bin(),
            "-p",
            prompt,
            "--output-format",
            "json",
            "--permission-mode",
            "acceptEdits",
            "--allowedTools",
            self.settings.code_agent_allowed_tools,
        ]
        env = dict(os.environ)
        token = self._setup_token()
        if token:
            env["CLAUDE_CODE_OAUTH_TOKEN"] = token

        run_cmd = self._run_cmd or _default_run_cmd
        code, out, err = run_cmd(
            argv, str(workdir), env, int(self.settings.code_agent_timeout_sec)
        )

        summary = self._parse_summary(out, err)
        files, diff = self._collect_changes(workdir, self._baselines[key])
        max_bytes = int(self.settings.code_diff_max_bytes)
        return CodeRunOutcome(
            ok=code == 0,
            summary=summary,
            workdir=str(workdir),
            files_changed=files,
            diff=diff[:max_bytes],
            log=(err or out)[-2000:],
        )

    def execute_chat(
        self,
        *,
        goal: str,
        plan: Optional[Dict[str, Any]],
        feedback: Optional[Dict[str, Any]],
        workdir: Path,
    ) -> CodeRunOutcome:
        """Chat-mode agent session: one full headless Claude session per attempt.

        Runs in the team's memory dir so the session auto-loads that team's
        CLAUDE.md and can keep durable notes — the NanoClaw per-group model.
        The session's final text IS the draft the reviewer judges.
        """
        workdir.mkdir(parents=True, exist_ok=True)
        prompt = self._build_chat_prompt(goal, plan, feedback)
        argv = [
            self._resolve_bin(),
            "-p",
            prompt,
            "--output-format",
            "json",
            "--permission-mode",
            "acceptEdits",
            "--allowedTools",
            self.settings.chat_agent_allowed_tools,
        ]
        env = dict(os.environ)
        token = self._setup_token()
        if token:
            env["CLAUDE_CODE_OAUTH_TOKEN"] = token

        run_cmd = self._run_cmd or _default_run_cmd
        code, out, err = run_cmd(
            argv, str(workdir), env, int(self.settings.code_agent_timeout_sec)
        )
        summary = self._parse_summary(out, err)
        return CodeRunOutcome(
            ok=code == 0 and bool(summary.strip()),
            summary=summary,
            workdir=str(workdir),
            log=(err or out)[-2000:],
        )

    def _build_chat_prompt(
        self,
        goal: str,
        plan: Optional[Dict[str, Any]],
        feedback: Optional[Dict[str, Any]],
    ) -> str:
        plan_txt = json.dumps(plan or {}, indent=2)[:_PROMPT_SECTION_CAP]
        parts = [
            "You are the executor agent of a T-Ex team. The current directory is "
            "this team's persistent memory: CLAUDE.md holds team context and "
            "notes.md holds durable notes from earlier runs — read them if "
            "present, and append anything worth remembering to notes.md.",
            f"Goal: {goal}",
            f"Plan from the planner:\n{plan_txt}",
        ]
        if feedback and not feedback.get("passed", True):
            fb = json.dumps(feedback, indent=2)[:_PROMPT_SECTION_CAP]
            parts.append(
                "A reviewer rejected the previous attempt. Address this feedback "
                f"in your next answer:\n{fb}"
            )
        parts.append(
            "Rules: never write or print secret values; work only inside the "
            "current directory when writing files. Your FINAL message must be "
            "the complete deliverable for the goal (not a description of it)."
        )
        return "\n\n".join(parts)

    def run_verify(self, command: str, workdir: Path) -> Dict[str, Any]:
        """Run the done-gate command in the workdir. Exit 0 is the only pass.

        Deliberately NOT routed through the injectable run_cmd: verification is
        the honesty gate, so it always executes for real — tests use real shell
        commands (e.g. `test -f file`) instead of fakes.
        """
        shell = shutil.which("bash") or shutil.which("sh") or "sh"
        code, out, err = _default_run_cmd(
            [shell, "-c", command],
            str(workdir),
            dict(os.environ),
            int(self.settings.code_agent_timeout_sec),
        )
        output = ((out or "") + (("\n" + err) if err else "")).strip()
        return {
            "command": command,
            "exit_code": code,
            "ok": code == 0,
            "output": output[-4000:],
        }

    def _build_prompt(
        self,
        goal: str,
        plan: Optional[Dict[str, Any]],
        feedback: Optional[Dict[str, Any]],
    ) -> str:
        plan_txt = json.dumps(plan or {}, indent=2)[:_PROMPT_SECTION_CAP]
        parts = [
            "You are the executor of a T-Ex agent team. Do the work FOR REAL in the "
            "current directory: create and edit files, run quick local checks. "
            "Do not just describe the work.",
            f"Goal: {goal}",
            f"Plan from the planner:\n{plan_txt}",
        ]
        if feedback and not feedback.get("passed", True):
            fb = json.dumps(feedback, indent=2)[:_PROMPT_SECTION_CAP]
            parts.append(
                "A reviewer rejected the previous attempt. Address this feedback "
                f"by changing files (the workdir still has your previous work):\n{fb}"
            )
        parts.append(
            "Rules: work only inside the current directory; keep changes focused on "
            "the goal; never write or print secret values; when finished, print a "
            "short summary of what you changed."
        )
        return "\n\n".join(parts)

    def _setup_token(self) -> str:
        try:
            from texllm.host.credentials import resolve_runtime

            rt = resolve_runtime()
            if (rt.get("method") or "") == "setup_token":
                return (rt.get("api_key") or "").strip()
        except Exception:  # noqa: BLE001
            pass
        return ""

    @staticmethod
    def _parse_summary(out: str, err: str) -> str:
        text = (out or "").strip()
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                result = data.get("result")
                if isinstance(result, str) and result.strip():
                    return result.strip()
        except json.JSONDecodeError:
            pass
        return (text or err or "").strip()[-1500:]

    # ----- change detection -----

    def _snapshot(self, workdir: Path) -> Any:
        if self._is_git(workdir):
            code, out, _ = self._git(workdir, "status", "--porcelain")
            return {"git": True, "status": set(out.splitlines()) if code == 0 else set()}
        files: Dict[str, Tuple[int, int]] = {}
        count = 0
        for path in workdir.rglob("*"):
            if count >= _SCAN_CAP:
                break
            if any(part in _SKIP_DIRS for part in path.parts):
                continue
            if path.is_file():
                st = path.stat()
                files[str(path.relative_to(workdir))] = (st.st_size, st.st_mtime_ns)
                count += 1
        return {"git": False, "files": files}

    def _collect_changes(
        self, workdir: Path, baseline: Any
    ) -> Tuple[List[str], str]:
        if baseline.get("git"):
            return self._collect_git_changes(workdir, baseline)
        return self._collect_scan_changes(workdir, baseline)

    def _collect_git_changes(
        self, workdir: Path, baseline: Any
    ) -> Tuple[List[str], str]:
        own_run_dir = Path(self.settings.code_runs_dir).resolve() in workdir.resolve().parents
        if own_run_dir:
            # Scratch dir we created: stage everything for a complete diff
            # (tracked + previously-untracked files).
            self._git(workdir, "add", "-A")
            _, names, _ = self._git(workdir, "diff", "--cached", "--name-only")
            _, diff, _ = self._git(workdir, "diff", "--cached")
            files = [n for n in names.splitlines() if n.strip()]
            return files, diff

        # A user's directory: never touch the index. Report entries whose
        # porcelain status changed since baseline; diff covers tracked files.
        _, out, _ = self._git(workdir, "status", "--porcelain")
        before: set = baseline.get("status") or set()
        changed_lines = [ln for ln in out.splitlines() if ln and ln not in before]
        files = [ln[3:].strip() for ln in changed_lines]
        _, diff, _ = self._git(workdir, "diff", "HEAD")
        return files, diff

    def _collect_scan_changes(
        self, workdir: Path, baseline: Any
    ) -> Tuple[List[str], str]:
        before: Dict[str, Tuple[int, int]] = baseline.get("files") or {}
        after = self._snapshot(workdir)["files"]
        changed = [
            rel
            for rel, sig in after.items()
            if rel not in before or before[rel] != sig
        ]
        changed.sort()
        # Synthetic new-file diff so reviewers still see content without git
        chunks: List[str] = []
        budget = _SYNTH_DIFF_FILE_CAP
        for rel in changed:
            if budget <= 0:
                chunks.append(f"(diff truncated; more files changed: {rel} …)")
                break
            path = workdir / rel
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            header = "new file" if rel not in before else "modified"
            body = content[:budget]
            budget -= len(body)
            lines = "\n".join(f"+{ln}" for ln in body.splitlines())
            chunks.append(f"--- {header}: a/{rel}\n+++ b/{rel}\n{lines}")
        return changed, "\n\n".join(chunks)

    @staticmethod
    def _is_git(workdir: Path) -> bool:
        return (workdir / ".git").exists() and bool(shutil.which("git"))

    @staticmethod
    def _git(workdir: Path, *args: str) -> Tuple[int, str, str]:
        try:
            proc = subprocess.run(
                ["git", "-C", str(workdir), *args],
                capture_output=True,
                text=True,
                timeout=60,
            )
            return proc.returncode, proc.stdout, proc.stderr
        except (OSError, subprocess.TimeoutExpired) as exc:
            return 1, "", str(exc)
