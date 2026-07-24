# Playbook: Orchestrator (any terminal AI / API)

You are operating inside the **T-ex LLM** monorepo. Route work to the right playbook.

## When the user wants…

| Intent | Load next |
|--------|-----------|
| Host server, deploy, API, queues | `playbooks/01-host.md` |
| Team workers, runners, roles | `playbooks/02-workers.md` |
| Models, tools, memory, evals | `playbooks/03-ml-engineer.md` |
| Custom agent packages for products | `playbooks/04-firmware.md` |
| Wire agents into apps/platforms | `playbooks/05-integrate.md` |

## Default operating rules

1. Prefer **team-based runners** over single-agent freestyle.
2. Keep everything **model-agnostic** (env-based provider config).
3. Ship agents as **firmware**: versioned, tested, documented I/O.
4. Never commit secrets; use `.env.example` only.
5. If the task spans layers, sequence: design → workers → host → firmware → integrate.

## Output contract

Always state: goal, chosen playbook(s), files you will touch, acceptance criteria.
