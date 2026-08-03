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
| POST | `/v1/workspace/teams/{slug}/run-async` |
| GET | `/v1/channels` |
| GET/POST | `/v1/channels/{channel}/webhook` |
| POST | `/v1/workspace/domain-review` |

Messaging channels (Telegram / WhatsApp / Google Chat / BlueBubbles-iMessage /
custom HMAC) dispatch team runs from chat — setup, security model, and the
adapter plugin contract live in `docs/CHANNELS.md`.
| GET | `/v1/workspace/ideas` |
| POST | `/v1/workspace/brains` |
| POST | `/v1/workspace/skills` |
| POST | `/v1/workspace/personal-bd/run` |

## Team dashboard UX

- **KPI cards** — per-team metrics (editable +/−)
- **Kanban board** — backlog → todo → doing → review → done
- **Export brains → firmware** — `tex export <team>` writes `firmware/<team>-agents/`

## Flow

```
Domain review ──► ideas + brains + skills (SQLite)
                      │
Team dashboard (KPI + kanban) ◄──┤
                      │
tex export <team> ──► firmware/<team>-agents/
                      │
tex @sales / Web run ─┴──► TeamRunner (prefers exported firmware)
```

## Export firmware

```bash
tex export sales
# → firmware/sales-agents/manifest.yaml + prompts from brains
tex run sales "Weekly pipeline review"   # uses sales-agents if present
```

## Code mode — runs that do real work

By default a run is a text loop (planner → executor drafts prose → reviewer →
integrator). With `--code`, the executor instead drives a **headless Claude Code
session** that edits files for real; the reviewer reviews the actual diff and the
job result carries `workdir`, `files_changed`, and `diff`.

```bash
tex run dev --code "Create healthz.py with a /healthz FastAPI route"
# isolated workdir: .texllm/runs/<job-id>/  (git-inited → full diff artifact)

tex run dev --code --workdir ~/myapp "Fix the failing date parser"
# runs in-place in an existing directory (your responsibility to review/commit)
```

Same over HTTP: `POST /v1/workspace/teams/{slug}/run` or `/run-async` with
`{"goal": "...", "mode": "code", "workdir": "(optional)"}` — `/run-async` returns a
`job_id` immediately; poll `GET /v1/jobs/{job_id}` (this is what the Command Deck's
Run Ops tab uses).

Honest-failure contract: code mode requires the `claude` CLI on the host's PATH
(`ANTHROPIC` login or `CLAUDE_CODE_OAUTH_TOKEN` setup-token profile). If it's
missing, the job **fails with a clear error** — it never silently falls back to
prose. Env knobs: `CODE_AGENT_BIN`, `CODE_AGENT_TIMEOUT_SEC`,
`CODE_AGENT_ALLOWED_TOOLS`, `CODE_RUNS_DIR`, `CODE_DIFF_MAX_BYTES`.
