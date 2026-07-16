---
name: agentic-host
description: Build and deploy the T-ex LLM host server (API, queues, workers, observability). Use when the user says host runtime, deploy agents, agent API, job queue, or runs /agentic-host.
---

# Agentic host

Follow `playbooks/01-host.md` in this repo.

## Steps

1. Read `docs/architecture.md` and `playbooks/01-host.md`.
2. Implement or extend code under `host/`.
3. Keep config env-driven and model-agnostic.
4. Wire jobs to team runners from `playbooks/02-workers.md`.
5. Add/update `.env.example` and a minimal run command in README.
6. Verify: health endpoint + one end-to-end job create/poll.

Works in Grok, Claude Code, Codex, or any agent that can read this file.
