"""Deterministic mock LLM for offline demos and tests."""

from __future__ import annotations

import json
import re
from typing import List, Optional

from texllm.providers.base import ChatMessage, CompletionResult, LLMProvider


class MockProvider(LLMProvider):
    name = "mock"

    def complete(
        self,
        messages: List[ChatMessage],
        *,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> CompletionResult:
        system = " ".join(m.content for m in messages if m.role == "system").lower()
        user = " ".join(m.content for m in messages if m.role == "user")
        goal = _extract_goal(user)

        if "planner" in system:
            content = json.dumps(
                {
                    "plan": [
                        f"Clarify goal: {goal}",
                        "Gather facts with tools if needed",
                        "Draft answer",
                        "Verify against success criteria",
                    ],
                    "success_criteria": [
                        "Addresses the user goal directly",
                        "Includes concrete next steps",
                        "Is clear and structured",
                    ],
                    "notes": "Mock planner output",
                },
                indent=2,
            )
        elif "reviewer" in system:
            # Fail once if draft is empty/too short so retry path is exercised in tests
            draft_match = re.search(r"Draft:\s*(.*)", user, re.S | re.I)
            draft = (draft_match.group(1) if draft_match else "").strip()
            if len(draft) < 20 or "PLACEHOLDER_FAIL" in draft:
                content = json.dumps(
                    {
                        "passed": False,
                        "feedback": "Draft is too thin; expand with specifics and next steps.",
                        "score": 0.3,
                    }
                )
            else:
                content = json.dumps(
                    {
                        "passed": True,
                        "feedback": "Meets success criteria.",
                        "score": 0.9,
                    }
                )
        elif "integrator" in system:
            content = json.dumps(
                {
                    "summary": f"Completed: {goal}",
                    "output": {
                        "answer": _extract_section(user, "Draft")
                        or f"Mock result for: {goal}",
                        "goal": goal,
                    },
                },
                indent=2,
            )
        else:
            # executor
            content = (
                f"## Answer\n\n"
                f"Regarding **{goal}**:\n\n"
                f"1. Understand requirements and constraints.\n"
                f"2. Break work into small verifiable steps.\n"
                f"3. Use team runners (plan → execute → review).\n"
                f"4. Package the agent as versioned firmware for your product.\n\n"
                f"### Next steps\n"
                f"- Run the host API and submit a job\n"
                f"- Pin firmware version in production\n"
                f"- Add evals for regressions\n"
            )

        return CompletionResult(
            content=content,
            model=model or "mock-model",
            provider=self.name,
            usage_tokens=max(1, len(content) // 4),
        )


def _extract_goal(user: str) -> str:
    m = re.search(r"Goal:\s*(.+)", user, re.I)
    if m:
        return m.group(1).strip().splitlines()[0]
    return user.strip().splitlines()[0][:200] if user.strip() else "unspecified goal"


def _extract_section(text: str, name: str) -> str:
    m = re.search(rf"{name}:\s*(.*?)(?:\n[A-Z][a-z]+:|\Z)", text, re.S)
    return m.group(1).strip() if m else ""
