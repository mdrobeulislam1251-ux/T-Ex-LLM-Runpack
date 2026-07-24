# T-Ex LLM

One agent, three brains: **dev + operations + strategy**, wrapped in an execution-first behavior contract. Built to work on **any system** — nothing is hardcoded; T-Ex probes the environment it wakes up in.

## Launch

```powershell
# From any project directory:
& "<path-to-this-folder>\launch-tex.ps1"
```

The launcher sets `CLAUDE_CONFIG_DIR` to the `.claude-tex` home next to it, then starts Claude Code in your current directory. Move this whole folder anywhere — any drive, any machine — and it still works.

## Alternative installs

- **Per-project:** copy `.claude-tex/skills/*` into a project's `.claude/skills/` — the skills auto-load only in that project.
- **Global:** copy the skills into `%USERPROFILE%\.claude\skills\` to have them in every default session.

## What's inside

| Layer | Skills |
|---|---|
| Agentic core | `environment-recon`, `execution-discipline`, `verification-gates`, `project-bootstrap` |
| Dev | `api-design`, `fullstack-delivery`, `systematic-debugging`, `ui-ux-design`, `app-security` |
| Data engineering | `postgres-patterns`, `supabase-platform`, `sql-analytics`, `elasticsearch-opensearch`, `clickhouse-analytics`, `data-pipelines` |
| Ops / DevOps | `server-ops-safety`, `network-diagnosis`, `docker-operations`, `grafana-observability`, `devops-cicd` |
| Strategy | `product-gtm-strategy`, `b2b-outbound-pipeline` |

Persona and behavior contract: `.claude-tex/CLAUDE.md`.

## Design rules (enforced in every skill)

1. No absolute paths, hostnames, usernames, or credentials — environment facts are probed at runtime.
2. A skill earns its file only if it carries real payload: exact commands, verbatim error→fix tables, numeric thresholds, or enforceable behavioral gates.
3. Done = run-verified. Exit 0 is "compiled", not "works".
