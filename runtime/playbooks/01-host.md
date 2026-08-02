# Playbook: Host server

Build and operate the **host runtime** that runs agent workers safely.

## Responsibilities

- HTTP/gRPC (or similar) API for jobs, status, results
- Authn/authz for multi-tenant product use
- Job queue + worker pool
- Observability: logs, traces, metrics
- Config: model providers, tool allowlists, rate limits
- Deploy: Docker/K8s or simple process supervisor

## Implementation checklist

1. Define job schema: `id`, `firmware_id`, `input`, `status`, `result`, `error`.
2. Expose endpoints: create job, get job, cancel job, health.
3. Wire queue → worker runners (see `02-workers.md`).
4. Isolate tool permissions per firmware package.
5. Add health + readiness probes and structured logging.
6. Document env vars in `.env.example`.

## Acceptance criteria

- Can submit a job and poll until `succeeded` / `failed`.
- Workers restart safely; no silent job loss.
- Secrets never logged.
