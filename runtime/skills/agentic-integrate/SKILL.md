---
name: agentic-integrate
description: Integrate T-ex LLM agents into customer platforms and apps (SDK, webhooks, embed). Use when the user says integrate agents, product SDK, webhooks, embed agent, or runs /agentic-integrate.
---

# Agentic integrate

Follow `playbooks/05-integrate.md` in this repo.

## Steps

1. Define public API / webhook contract.
2. Implement tenant auth and isolation.
3. Provide SDK stubs (TS and/or Python).
4. Add `examples/integrate-demo/`.
5. Verify signed webhook + create-job flow.

Works in Grok, Claude Code, Codex, or any agent that can read this file.
