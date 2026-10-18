---
name: agentic-platform
description: Orchestrator for the T-ex LLM multi-skill suite — routes host, workers, ML, firmware, and integrate work. Use when the user says T-ex LLM, agentic platform, multi-agent product, or runs /agentic-platform.
---

# Agentic platform (orchestrator)

Follow `playbooks/00-orchestrator.md`.

## Route to skills

| Need | Skill / playbook |
|------|------------------|
| Host / deploy | `agentic-host` → `playbooks/01-host.md` |
| Team runners | `agentic-workers` → `playbooks/02-workers.md` |
| Models / evals | `agentic-ml-engineer` → `playbooks/03-ml-engineer.md` |
| Product packages | `agentic-firmware` → `playbooks/04-firmware.md` |
| App wiring | `agentic-integrate` → `playbooks/05-integrate.md` |

## Rules

1. Team runners over solo agents.
2. Model-agnostic config.
3. Firmware is the product unit.
4. No secrets in git.

State goal, route, files, and acceptance criteria before coding.
