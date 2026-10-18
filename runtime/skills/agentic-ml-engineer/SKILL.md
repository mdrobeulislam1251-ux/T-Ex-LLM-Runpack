---
name: agentic-ml-engineer
description: ML-native agent engineering for T-ex LLM — providers, tools, memory, routing, evals, guardrails. Use when the user says model provider, tool registry, evals, agent memory, or runs /agentic-ml-engineer.
---

# Agentic ML engineer

Follow `playbooks/03-ml-engineer.md` in this repo.

## Steps

1. Keep providers swappable via env (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`).
2. Typed tools + schema validation before side effects.
3. Structured outputs between workers.
4. Add/maintain evals for regressions.
5. Document model routing policy (cheap vs strong).

Works in Grok, Claude Code, Codex, or any agent that can read this file.
