# T-ex multi-team agent workspace

One **shared SQLite database** powers the **web UI** and the **`tex` CLI** (Claude Code `@T-ex`).

DB file: `.texllm/workspace.db`

## Teams (seeded)

| Slug | Dashboard |
|------|-----------|
| `ops` | Operations |
| `sales` | Sales |
| `dev` | Engineering |
| `tech` | Tech / Platform |
| `ceo` | CEO / Exec |
| `fulfillment` | Fulfillment |
| `personal-bd` | Personal Business Development agent |

Customers can add more teams via UI or API (`POST /v1/workspace/teams`).

## Features

1. **Team agentic dashboards** — brains, skills, flows, activity  
2. **Domain / website review** — fetch site → generate ideas → create brains & skills  
3. **Personal BD agent** — same backend, team `personal-bd`  
4. **Custom web UI** — Workspace + team pages  
5. **CLI / Claude Code** — `tex` or `@T-ex` / `@sales` …

## CLI

```bash
pip install -e .
tex teams
tex dash ceo
tex run sales "Weekly pipeline review"
tex review example.com
tex bd "Intro path to 3 design partners"
tex @T-ex "Coordinate ops and sales handoff"
```

## API

| Method | Path |
|--------|------|
| GET | `/v1/workspace` |
| GET | `/v1/workspace/teams` |
| POST | `/v1/workspace/teams` |
| GET | `/v1/workspace/teams/{slug}` |
| POST | `/v1/workspace/teams/{slug}/run` |
| POST | `/v1/workspace/domain-review` |
| GET | `/v1/workspace/ideas` |
| POST | `/v1/workspace/brains` |
| POST | `/v1/workspace/skills` |
| POST | `/v1/workspace/personal-bd/run` |

## Flow

```
Domain review ──► ideas + brains + skills (SQLite)
                      │
Team dashboard ◄──────┤
                      │
tex @sales / Web run ─┴──► TeamRunner (Claude-first provider)
```
