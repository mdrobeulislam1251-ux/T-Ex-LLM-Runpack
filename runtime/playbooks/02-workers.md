# Playbook: Team-based workers / runners

Implement **accurate multi-agent workers** (team runners preferred over solo agents).

## Preferred team shape

| Role | Duty |
|------|------|
| Planner | Break task into steps + success criteria |
| Executor(s) | Do work with scoped tools |
| Reviewer | Verify against criteria; request rework |
| Integrator | Format final payload for host/API |

## Rules

1. Each role has a **narrow tool allowlist**.
2. Handoffs are explicit messages with structured state (JSON preferred).
3. Max iteration / cost budgets per job.
4. Reviewer can reject; loop until pass or budget exhausted.
5. Persist intermediate artifacts for auditability.

## Implementation checklist

1. Define role configs (prompt, tools, model tier).
2. Implement runner loop: plan → execute → review → integrate.
3. Shared job state store (memory OK for MVP; durable later).
4. Unit tests for handoff schema and budget enforcement.
5. Example team under `examples/`.

## Acceptance criteria

- Demo job completes with planner + executor + reviewer.
- Failed review triggers one controlled retry path.
- Clear final result schema.
