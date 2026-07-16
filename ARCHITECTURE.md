# Arion — System Architecture & Initialization Schema

> **Path note.** The originating initialization brief referenced a Windows
> root (`E:\Robeul's Ai Assistant`). This repository is the canonical,
> cross-platform home of the system; all paths below are **relative to the
> repository root** and are real, on-disk paths — no invented absolute paths.

## 1. Multi-tenant file tree (as initialized)

```
Arion-Multi-Agent/
├── arion.py                          # CLI entrypoint (route | list | schema)
├── tasks.md                          # TDD execution roadmap (RED→GREEN→REFACTOR)
├── ARCHITECTURE.md                   # this file
├── README.md
│
├── config/
│   └── routing.json                  # authoritative keyword → workspace map
│
├── core_router_test.py               # SKILL.md TDD gate (portable, 3 tests)
│
├── core/
│   ├── __init__.py
│   ├── router.py                     # keyword-triggered routing engine
│   ├── engine.py                     # agent execution engine (registry + dispatch)
│   └── hooks.py                      # runtime hook layer (lifecycle + QueryHook)
│
├── tests/
│   ├── __init__.py
│   ├── test_router.py                # 17 TDD tests (config, routing, scoring, schema)
│   ├── test_engine.py                # 6 TDD tests (dispatch, guards, metadata)
│   └── test_hooks.py                 # 4 TDD tests (route+dispatch, lifecycle order)
│
├── App Dev and Engineering Team/     # TRACK 1 — engines, hooks, deployments
│   ├── README.md
│   ├── SKILL.md                      #   Intent Hooks + code-gen/TDD/SSH/Playwright rules
│   ├── agents/                       #   → agent execution engines & orchestration
│   │   └── README.md
│   ├── runtime_hooks/                #   → runtime hooks, lifecycle interceptors
│   │   └── README.md
│   └── deployments/                  #   → Tailnet SSH (tl-host) + Playwright
│       └── README.md
│
└── Robeul's Workspace Assistant/     # TRACK 2 — tasks, tool handlers, pipelines
    ├── README.md
    ├── SKILL.md                      #   Global routing Intent Hooks + execution rules
    ├── tasks/                        #   → task/roadmap/backlog management
    │   ├── README.md
    │   └── inbox/                    #   → DEFAULT fallback for unrouted queries
    │       └── README.md
    ├── gmail/                        #   → Gmail intent-hook skill home
    │   └── README.md
    ├── asana/                        #   → Asana intent-hook skill home
    │   └── README.md
    ├── support/                      #   → support intent-hook skill home
    │   └── README.md
    ├── tool_handlers/                #   → low-level Gmail / Asana / calendar adapters
    │   └── README.md
    └── pipelines/                    #   → support & workflow automation
        └── README.md
```

## 2. Routing schema (`config/routing.json`)

Schema id: `arion.routing/v1`

| Field                    | Type     | Meaning                                                     |
| ------------------------ | -------- | ----------------------------------------------------------- |
| `version`                | string   | Config version.                                             |
| `default_route`          | object   | Destination when no keyword matches (catch-all).            |
| `routes[]`               | array    | Ordered routing rules.                                      |
| `routes[].name`          | string   | Stable route id.                                            |
| `routes[].track`         | string   | One of the two top-level tracks.                            |
| `routes[].workspace`     | string   | Target sub-agent folder (must be nested under `track`).     |
| `routes[].priority`      | int      | Tie-breaker; higher wins on equal keyword score.            |
| `routes[].keywords[]`    | string[] | Trigger phrases (word-boundary, case-insensitive matched).  |
| `routes[].description`   | string   | Human-readable routing rationale.                           |

## 3. Keyword-trigger routing flow

```
task query
    │
    ▼
Router.route(query)                        (core/router.py)
    │   • compile keywords → word-boundary regex (multi-word aware)
    │   • score each route = Σ (tokens in each matched keyword)
    │   • tie-break: score ↓, priority ↓, config order ↑
    ▼
best RouteMatch  ──(score 0 for all)──▶  default_route  → tasks/inbox/
    │
    ▼
dispatch to  <track>/<workspace>           (owning sub-agent workspace)
```

**Scoring guarantees (all test-pinned):**

- A multi-word keyword (`execution engine`, 2 tokens) outranks an incidental
  single-word hit (`task`, 1 token).
- Substring collisions are rejected — `management` does **not** trigger the
  `agent` keyword.
- Empty / whitespace / unmatched queries deterministically fall to
  `Robeul's Workspace Assistant/tasks/inbox/`.

## 4. Active route table

| Route               | Track                        | Workspace                                        | Priority |
| ------------------- | ---------------------------- | ------------------------------------------------ | -------- |
| `agent-engineering` | App Dev and Engineering Team | `…/agents`                                        | 90       |
| `system-deployment` | App Dev and Engineering Team | `…/deployments`                                   | 85       |
| `runtime-hooks`     | App Dev and Engineering Team | `…/runtime_hooks`                                 | 80       |
| `external-tools`    | Robeul's Workspace Assistant | `…/tool_handlers`                                 | 75       |
| `task-management`   | Robeul's Workspace Assistant | `…/tasks`                                         | 70       |
| `support-pipelines` | Robeul's Workspace Assistant | `…/pipelines`                                     | 65       |
| *(default)*         | Robeul's Workspace Assistant | `…/tasks/inbox`                                   | —        |

## 5. Deployment pipeline (target design — Phase 6)

- **Sync branch:** `Robeul-Dev-Update`
- **Transport:** Tailnet IP mesh → SSH to `tl-host`
- **Post-deploy verification:** Playwright smoke test asserts the target is up.
- **TDD gate:** a failing dry-run/health-check test must exist before any real
  deploy step is implemented (see `tasks.md` Phase 6).

## 6. Verification

```bash
python3 -m unittest discover -s tests -v   # 17 tests, all green
python3 arion.py route "deploy to tl-host over tailnet"
python3 arion.py list
python3 arion.py schema
```
