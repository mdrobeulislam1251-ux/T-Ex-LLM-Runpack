---
name: agentic-firmware
description: Build versioned agentic firmware packages for products sold on T-ex LLM. Use when the user says agent firmware, agent package, sellable agent, manifest.yaml, or runs /agentic-firmware.
---

# Agentic firmware

Follow `playbooks/04-firmware.md` in this repo.

## Steps

1. Create/update package under `firmware/<name>/` with `manifest.yaml`.
2. Define roles, prompts, tools, policies, and I/O contract.
3. Add golden tests in the package.
4. Ensure host can load by id+version.
5. Document customer-facing README for the package.

Works in Grok, Claude Code, Codex, or any agent that can read this file.
