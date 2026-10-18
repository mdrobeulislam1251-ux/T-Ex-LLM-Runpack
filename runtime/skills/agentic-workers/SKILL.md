---
name: agentic-workers
description: Design and implement team-based agent workers/runners for T-ex LLM. Use when the user says multi-agent, team runner, worker pool, planner-executor-reviewer, or runs /agentic-workers.
---

# Agentic workers

Follow `playbooks/02-workers.md` in this repo.

## Steps

1. Prefer team runners (planner → executor → reviewer → integrator).
2. Implement under `workers/` with structured handoffs.
3. Enforce tool allowlists and cost/iteration budgets.
4. Add a demo path under `examples/`.
5. Verify with a scripted multi-role job.

Works in Grok, Claude Code, Codex, or any agent that can read this file.
