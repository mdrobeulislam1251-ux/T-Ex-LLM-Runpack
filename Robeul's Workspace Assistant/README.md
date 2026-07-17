# Robeul's Workspace Assistant

Track owning **task management, external tool handlers (Gmail / Asana / …),
and support pipelines** of the Arion multi-agent workspace.

Arion routes any task query whose keywords match this track's routes here.

| Workspace        | Purpose                                             | Trigger keywords (excerpt)              |
| ---------------- | --------------------------------------------------- | --------------------------------------- |
| `tasks/`         | Task management, roadmap tracking, backlog grooming | task, todo, roadmap, sprint, backlog    |
| `tasks/inbox/`   | **Default fallback** for unrouted queries           | *(none — catch-all)*                    |
| `tool_handlers/` | External tool handlers (Gmail, Asana, calendar, …)  | gmail, email, asana, calendar, notion   |
| `pipelines/`     | Support pipelines, notification fan-out, automation | support, pipeline, workflow, automation |

The authoritative keyword map lives in [`config/routing.json`](../config/routing.json).
Do not edit trigger keywords here — this table is documentation only.
