---
description: Run the full development pipeline for a feature or product under the active company brain
---

Run the standard build pipeline from the `orchestration-runpack` skill for: $ARGUMENTS

1. Verify an active company brain exists — otherwise route to `/onboard` first.
2. cpo: turn the request into a PRD with acceptance criteria and a not-building list.
3. solutions-architect + cto: architecture (gate: cto approval, logged in decisions.md).
4. data-engineer: schema per the `data-schema-design` skill (gate: cto APPROVED).
5. Design pipeline per the `design-core` skill when the feature has UI (gate:
   design-director approval).
6. engineering-manager: task plan in dependency order, each task owner + reviewer.
7. Engineers implement under the `fullstack-65` guardrails (TDD, zero-laziness).
8. qa-automation-engineer + regression-tester: verification (gate: green suites).
9. devops-engineer ships; technical-writer documents.

Run every phase in one continuous run — gates are agent-to-agent reviews, never user
pauses (`execution-discipline` → Full-Run Rule). Do not skip gates, and do not stop
between phases to ask permission to continue. Report per-phase progress in the FINAL
report: what shipped, what's pending, and any decision needed from the user — batched
into one ask if any exist.
