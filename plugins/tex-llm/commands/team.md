---
description: Show the 52-agent company roster, or dispatch a task to the right team
---

If $ARGUMENTS is empty: print the roster from the `orchestration-runpack` skill — the
9 teams, their 52 agents, and each agent's one-line purpose — plus which company brain
is currently active.

If $ARGUMENTS contains a task: act as ceo-orchestrator. Use the routing table in
`orchestration-runpack` to pick the owning agent and reviewer, state the routing
decision in one line, then dispatch the task to that agent under the active company
brain.
