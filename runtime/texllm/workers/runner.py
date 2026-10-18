"""Team-based runner: planner → executor → reviewer → integrator."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

from texllm.config import Settings, get_settings
from texllm.firmware.loader import FirmwarePackage, load_firmware
from texllm.providers import get_provider
from texllm.providers.base import ChatMessage, LLMProvider
from texllm.schemas import (
    Artifact,
    Handoff,
    Job,
    JobResult,
    JobStatus,
    RoleName,
    utcnow,
)
from texllm.tools.builtin import build_builtin_registry
from texllm.tools.registry import ToolRegistry
from texllm.workers.code_executor import CodeExecutor, CodeRunOutcome
from texllm.workers.state import TeamState

logger = logging.getLogger(__name__)


def _parse_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return {"raw": text}


def _compose_code_draft(outcome: "CodeRunOutcome") -> str:
    """Render the executor's real changes as the draft the reviewer judges."""
    files = "\n".join(f"- {f}" for f in outcome.files_changed) or "- (none)"
    diff_excerpt = (outcome.diff or "").strip()
    if len(diff_excerpt) > 6000:
        diff_excerpt = diff_excerpt[:6000] + "\n… (diff truncated for review)"
    return (
        f"{outcome.summary or 'Code run complete.'}\n\n"
        f"Working directory: {outcome.workdir}\n\n"
        f"Files changed ({len(outcome.files_changed)}):\n{files}\n\n"
        f"Diff:\n```diff\n{diff_excerpt or '(no textual diff available)'}\n```"
    )


class TeamRunner:
    """Accurate multi-agent loop with budgets and review retries."""

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        tools: Optional[ToolRegistry] = None,
        settings: Optional[Settings] = None,
        code_executor: Optional[CodeExecutor] = None,
    ) -> None:
        self.settings = settings or get_settings()
        # Lazy: resolving inside run_job means an unconfigured provider becomes
        # a failed job record (with the actionable error) instead of an
        # exception escaping a dispatch thread.
        self._provider = provider
        self.base_tools = tools or build_builtin_registry()
        self.code_executor = code_executor

    @property
    def provider(self) -> LLMProvider:
        if self._provider is None:
            self._provider = get_provider(self.settings)
        return self._provider

    def _chat_sessions_enabled(self) -> bool:
        """Agent sessions for chat runs — only when Claude itself is connected.

        Mock (explicit or test-forced) and plain API-key setups keep the
        single-shot completion loop; a subscription/CLI login means the real
        Claude Code engine is available, so use it for the whole task.
        """
        if not getattr(self.settings, "chat_agent_sessions", True):
            return False
        if os.environ.get("TEXLLM_FORCE_MOCK", "").strip() in ("1", "true", "yes"):
            return False
        if (self.settings.llm_provider or "").strip().lower() == "mock":
            return False
        try:
            from texllm.host.credentials import resolve_runtime

            return resolve_runtime().get("method") in ("setup_token", "local_cli")
        except Exception:  # noqa: BLE001
            return False

    def run_job(self, job: Job) -> Job:
        job.status = JobStatus.running
        job.started_at = utcnow()
        job.touch()

        try:
            fw = load_firmware(
                self.settings.firmware_dir,
                job.firmware_id,
                job.firmware_version,
            )
            result = self._run_team(job, fw)
            job.result = result
            job.status = JobStatus.succeeded
            job.error = None
        except Exception as exc:  # noqa: BLE001 — surface to job record
            logger.exception("Job %s failed", job.id)
            job.status = JobStatus.failed
            job.error = str(exc)
            job.result = None

        job.finished_at = utcnow()
        job.touch()
        return job

    def _run_team(
        self,
        job: Job,
        fw: FirmwarePackage,
    ) -> JobResult:
        goal = job.goal
        input_data = job.input
        limits = fw.manifest.limits
        max_iter = min(limits.max_iterations, self.settings.job_max_iterations)
        max_retries = limits.max_review_retries

        code_mode = (getattr(job, "mode", "chat") or "chat") == "code"
        code_outcome: Optional[CodeRunOutcome] = None
        executor: Optional[CodeExecutor] = None
        workdir = None
        # Programmatic done-gate: a shell command that must exit 0 before the
        # job may succeed. The model's own "done" claim is never sufficient.
        verify_cmd = (
            str(input_data.get("verify") or "").strip() if code_mode else ""
        )
        verify_result: Optional[Dict[str, Any]] = None
        chat_session = False
        if code_mode:
            executor = self.code_executor or CodeExecutor(settings=self.settings)
            if not executor.available():
                raise RuntimeError(
                    "code mode requires a coding agent CLI "
                    f"('{executor.agent_bin}') on PATH — install Claude Code, "
                    "or run without --code for a draft-only chat run."
                )
            workdir = executor.prepare_workdir(
                job.id, explicit=input_data.get("workdir")
            )
        elif self._chat_sessions_enabled():
            executor = self.code_executor or CodeExecutor(settings=self.settings)
            if executor.available():
                chat_session = True
                # Team memory dir (written by prepare_team_job) or a scratch
                # session dir — CLAUDE.md/notes.md there persist across runs.
                workdir = Path(
                    input_data.get("memory_dir")
                    or Path(self.settings.code_runs_dir) / job.id
                )

        state = TeamState(goal=goal, input=input_data)

        # 1) Plan
        state.plan = self._role_json(
            fw,
            RoleName.planner,
            user=(
                f"Goal: {goal}\n"
                f"Input: {json.dumps(input_data)}\n"
                "Return JSON with keys: plan (array of steps), success_criteria (array)."
            ),
            state=state,
        )
        state.add_handoff(
            Handoff(
                from_role=RoleName.planner,
                to_role=RoleName.executor,
                content="Plan ready",
                data=state.plan or {},
            )
        )
        state.artifacts.append(
            Artifact(name="plan", kind="json", content=state.plan)
        )
        state.iteration += 1

        # 2) Execute + review loop
        while state.review_retries <= max_retries and state.iteration < max_iter:
            if code_mode and executor is not None and workdir is not None:
                # Real work: a headless coding agent edits files in the workdir;
                # the draft the reviewer sees is the actual measured change.
                code_outcome = executor.execute(
                    goal=goal,
                    plan=state.plan,
                    feedback=state.review,
                    workdir=workdir,
                )
                if not code_outcome.ok and not code_outcome.files_changed:
                    raise RuntimeError(
                        "code executor failed without producing changes: "
                        f"{(code_outcome.log or code_outcome.summary)[-500:]}"
                    )
                state.tool_log.append(
                    {
                        "tool": "code_agent",
                        "ok": code_outcome.ok,
                        "files_changed": code_outcome.files_changed,
                    }
                )
                state.draft = _compose_code_draft(code_outcome)
                if verify_cmd:
                    verify_result = executor.run_verify(verify_cmd, workdir)
                    state.tool_log.append({"tool": "verify", **verify_result})
                    state.draft += (
                        f"\n\nVerification `{verify_cmd}` → exit "
                        f"{verify_result['exit_code']} "
                        f"({'PASS' if verify_result['ok'] else 'FAIL'})\n"
                        f"```\n{verify_result['output'][-1500:]}\n```"
                    )
            elif chat_session and executor is not None and workdir is not None:
                # NanoClaw model: one full headless Claude session does the
                # task in the team's memory dir. Its final text is the draft.
                session = executor.execute_chat(
                    goal=goal,
                    plan=state.plan,
                    feedback=state.review,
                    workdir=workdir,
                )
                if not session.ok:
                    raise RuntimeError(
                        "chat agent session failed: "
                        f"{(session.log or session.summary or 'no output')[-500:]}"
                    )
                state.tool_log.append(
                    {"tool": "agent_session", "ok": True, "workdir": session.workdir}
                )
                state.draft = session.summary
            else:
                state.draft = self._role_text(
                    fw,
                    RoleName.executor,
                    user=(
                        f"Goal: {goal}\n"
                        f"Plan: {json.dumps(state.plan)}\n"
                        f"Input: {json.dumps(input_data)}\n"
                        f"Previous feedback: {json.dumps(state.review)}\n"
                        "Write the best draft answer. You may mention tools conceptually; "
                        "host will run declared tools when needed."
                    ),
                    state=state,
                )
                # Optional lightweight tool use from plan keywords
                self._maybe_run_tools(fw, state)

            handoff_data: Dict[str, Any] = {"draft_preview": state.draft[:500]}
            if code_outcome is not None:
                handoff_data["files_changed"] = code_outcome.files_changed
            state.add_handoff(
                Handoff(
                    from_role=RoleName.executor,
                    to_role=RoleName.reviewer,
                    content="Draft ready",
                    data=handoff_data,
                )
            )
            state.iteration += 1

            state.review = self._role_json(
                fw,
                RoleName.reviewer,
                user=(
                    f"Goal: {goal}\n"
                    f"Success criteria: {json.dumps((state.plan or {}).get('success_criteria', []))}\n"
                    f"Draft:\n{state.draft}\n"
                    "Return JSON: {passed: bool, feedback: string, score: number}."
                ),
                state=state,
            )
            state.add_handoff(
                Handoff(
                    from_role=RoleName.reviewer,
                    to_role=RoleName.executor
                    if not state.review.get("passed")
                    else RoleName.integrator,
                    content="Review complete",
                    data=state.review,
                )
            )
            state.iteration += 1

            gate_ok = bool(state.review.get("passed"))
            if verify_cmd:
                verify_ok = bool(verify_result and verify_result.get("ok"))
                if gate_ok and not verify_ok:
                    # The machine gate overrides an approving reviewer: an
                    # unverified draft is not done, whatever the model says.
                    state.review = {
                        "passed": False,
                        "feedback": (
                            "Reviewer approved the draft, but the verification "
                            f"command `{verify_cmd}` failed (exit "
                            f"{(verify_result or {}).get('exit_code')}). Fix the "
                            "code until it passes:\n"
                            f"{(verify_result or {}).get('output', '')[-800:]}"
                        ),
                        "score": 0.0,
                    }
                gate_ok = gate_ok and verify_ok
            if gate_ok:
                break
            state.review_retries += 1
            logger.info(
                "Review rejected (retry %s): %s",
                state.review_retries,
                state.review.get("feedback"),
            )

        if verify_cmd and not (verify_result and verify_result.get("ok")):
            raise RuntimeError(
                f"verification gate failed: `{verify_cmd}` exited "
                f"{(verify_result or {}).get('exit_code', 'n/a')} after "
                f"{state.review_retries} retr{'y' if state.review_retries == 1 else 'ies'} "
                f"(workdir: {workdir}). Last output:\n"
                f"{(verify_result or {}).get('output', '(none)')[-800:]}"
            )

        # 3) Integrate
        state.final = self._role_json(
            fw,
            RoleName.integrator,
            user=(
                f"Goal: {goal}\n"
                f"Draft:\n{state.draft}\n"
                f"Review: {json.dumps(state.review)}\n"
                f"Tool log: {json.dumps(state.tool_log)}\n"
                "Return JSON: {summary: string, output: object}."
            ),
            state=state,
        )
        state.add_handoff(
            Handoff(
                from_role=RoleName.integrator,
                content="Final payload",
                data=state.final or {},
            )
        )
        state.iteration += 1

        passed = bool((state.review or {}).get("passed"))
        summary = str((state.final or {}).get("summary") or state.draft[:200])
        output = (state.final or {}).get("output")
        if not isinstance(output, dict):
            output = {"answer": state.draft, "review": state.review}

        if chat_session and workdir is not None:
            output["mode"] = "agent_session"
            output["memory_dir"] = str(workdir)

        if code_outcome is not None:
            # Real-change evidence travels with the result, not just prose.
            output["mode"] = "code"
            output["workdir"] = code_outcome.workdir
            output["files_changed"] = code_outcome.files_changed
            output["diff"] = code_outcome.diff
            if verify_result is not None:
                output["verify"] = verify_result
            state.artifacts.append(
                Artifact(
                    name="files_changed",
                    kind="json",
                    content=code_outcome.files_changed,
                )
            )
            state.artifacts.append(
                Artifact(
                    name="diff",
                    kind="diff",
                    content=code_outcome.diff or "(no textual diff available)",
                )
            )
            state.artifacts.append(
                Artifact(
                    name="code_run",
                    kind="json",
                    content={
                        "workdir": code_outcome.workdir,
                        "agent_ok": code_outcome.ok,
                        "agent_summary": code_outcome.summary,
                    },
                )
            )

        return JobResult(
            summary=summary,
            output=output,
            artifacts=state.artifacts,
            review_passed=passed,
            iterations=state.iteration,
            handoffs=state.handoffs,
        )

    def _role_messages(
        self,
        fw: FirmwarePackage,
        role: RoleName,
        user: str,
    ) -> list:
        system = fw.prompt_for(role.value)
        tools = self.base_tools.allowlist(fw.tools_for(role.value))
        try:
            from texllm.host.aliases import alias_store

            address = alias_store.get().prompt_preamble()
        except Exception:  # noqa: BLE001
            address = ""
        system = (
            f"{system}\n\nYou are the **{role.value}** role.\n"
            f"{address}\n"
            f"Available tools (allowlist):\n{tools.describe_for_prompt()}\n"
            "Prefer structured output when asked for JSON."
        )
        return [
            ChatMessage(role="system", content=system),
            ChatMessage(role="user", content=user),
        ]

    def _complete(
        self,
        fw: FirmwarePackage,
        role: RoleName,
        user: str,
        state: TeamState,
    ) -> str:
        cfg = fw.role(role.value)
        temp = cfg.temperature if cfg else 0.2
        result = self.provider.complete(
            self._role_messages(fw, role, user),
            temperature=temp,
        )
        state.tokens_used += result.usage_tokens
        return result.content

    def _role_text(
        self,
        fw: FirmwarePackage,
        role: RoleName,
        user: str,
        state: TeamState,
    ) -> str:
        return self._complete(fw, role, user, state)

    def _role_json(
        self,
        fw: FirmwarePackage,
        role: RoleName,
        user: str,
        state: TeamState,
    ) -> Dict[str, Any]:
        return _parse_json(self._complete(fw, role, user, state))

    def _maybe_run_tools(self, fw: FirmwarePackage, state: TeamState) -> None:
        """Run a couple of safe tools for auditability (MVP heuristic)."""
        tools = self.base_tools.allowlist(fw.tools_for(RoleName.executor.value))
        if "word_count" in tools.tools and state.draft:
            try:
                out = tools.call("word_count", {"text": state.draft})
                state.tool_log.append({"tool": "word_count", "result": out})
            except Exception as exc:  # noqa: BLE001
                state.tool_log.append({"tool": "word_count", "error": str(exc)})
        if "checklist" in tools.tools and state.plan:
            steps = state.plan.get("plan") if isinstance(state.plan, dict) else None
            if isinstance(steps, list) and steps:
                try:
                    out = tools.call(
                        "checklist",
                        {"items": [str(s) for s in steps[:8]]},
                    )
                    state.tool_log.append({"tool": "checklist", "result": out})
                    state.artifacts.append(
                        Artifact(name="checklist", kind="json", content=out)
                    )
                except Exception as exc:  # noqa: BLE001
                    state.tool_log.append({"tool": "checklist", "error": str(exc)})
