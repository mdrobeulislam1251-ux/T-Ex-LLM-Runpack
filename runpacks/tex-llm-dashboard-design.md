# T-Ex LLM Dashboard — Design Runpack

The design vision for the T-Ex LLM web UI: an **agentic command deck** that sits on top of the **local, terminal-based** runpack. The terminal (Claude Code running the `tex-llm` plugin) is the engine and the source of truth; the dashboard is the cockpit that lets you *watch the company work and steer it*. Local-only, git-native, no cloud, no secrets in the UI.

This extends the existing Command Deck (`dashboard/`, Next.js, port 4100, `/api/runpack` · `/api/active` · `/api/brain`) — it is an evolution, not a rewrite.

## 0. Principles (non-negotiable)

1. **Terminal is truth; UI observes and directs — never replaces.** Anything the UI does resolves to a file the terminal reads, or a command it runs. Close the browser and nothing breaks.
2. **Agentic, not admin.** Agents, teams, gates, and brains are first-class living actors on screen — not rows in a settings table.
3. **Git-native.** Every state is a file (`companies/`, `strategy/`, `plugins/tex-llm/`, logs). The UI reads and writes files, so the whole company versions like code.
4. **Local & private.** Runs on `localhost`, `noindex`, no public surface, no external calls. Secrets are referenced by env-var NAME only — the dashboard never reads a value.
5. **One intent per view.** Every screen answers one audience's 3–5 questions (see `dashboard-design` skill). A widget that answers none is deleted.
6. **Brand from the active brain.** Chrome is the T-Ex system look (dark deck, one restrained accent); the *content* re-skins to the active company's brand tokens. Switching company visibly re-themes.

## 1. The terminal ↔ dashboard bridge (the core of "works with local terminal")

Three channels. This is what makes it agentic and live rather than a static file viewer.

```
        ┌─────────────────────────── your machine ───────────────────────────┐
        │                                                                     │
        │   Claude Code (terminal)            Dashboard (Next.js @ :4100)      │
        │   running tex-llm plugin                                            │
        │        │                                    │                        │
        │  READ  │  repo files ──────────────────▶  /api/runpack  (structure) │
        │        │  companies/ plugins/ strategy/     lib/data.ts loaders      │
        │        │                                    │                        │
        │  LIVE  │  hooks append events ─────────▶  .claude/tex-events.jsonl   │
        │        │  (SessionStart/PostToolUse/         │  file-watch → SSE      │
        │        │   SubagentStart|Stop/Stop)          ▼  /api/events (live)    │
        │        │                                   browser live feed          │
        │        │                                    │                        │
        │  WRITE │  terminal reads intent files ◀──  UI actions write files:    │
        │        │  active-company.json  ◀──────────  POST /api/active          │
        │        │  brain-request.json   ◀──────────  POST /api/brain           │
        │        │  <slug>/decisions.md  ◀──────────  POST /api/gate  (verdict) │
        │        │  tasks/*.json         ◀──────────  POST /api/task  (queue)   │
        │        └────────────────────────────────────┘                        │
        └─────────────────────────────────────────────────────────────────────┘
```

- **READ — structure/state:** already built. `/api/runpack` returns active brain, 9 teams, 53 agents, 44 skills, gate/decision logs.
- **LIVE — activity:** configure Claude Code **hooks** (in `settings.json`) to append one JSON line per event to `.claude/tex-events.jsonl` — `SessionStart`, `PostToolUse` (which skill/file/agent), `SubagentStart`/`SubagentStop` (team member wakes/finishes), `Stop`. The dashboard **tails that file** (fs-watch → Server-Sent Events) and streams it to the browser. This is the "watch your company work" feed.
- **WRITE — direct action:** UI actions write the exact intent files the terminal already consumes. Switch brain and create company exist today; add gate-verdict and task-queue files. Real-time *drive-the-terminal* stays file-based (git-native, simple, robust); Remote Control is an optional upgrade, not a dependency.
- **Honest constraint:** without a running session + hooks, the dashboard shows last-known **file state** (fully useful) and a clear "terminal not live" indicator. It lights up when `claude` is running with hooks wired. Design both states (§6).

## 2. Information architecture — views by intent

| View | Intent | The question it answers | Key content |
|---|---|---|---|
| **Command Deck** | monitor | "Is my company healthy, and what's happening right now?" | active brain, live activity feed, team status lanes, pending-gate count, session cost |
| **Roster** | explore | "Who does what?" | 9 team lanes → 53 agent cards → agent detail (persona + its skills) |
| **Brain Studio** | act | "Define or switch the company." | brain editor, `/onboard` flow, switch active, placeholder brains (consulti/trusted-leads/lead-gen-jay) |
| **Activity** | analyze | "What did the agents do, and why?" | chronological event stream, tool calls, hand-offs; filter by team/agent/session |
| **Gates & Decisions** | act | "What needs my approval?" | pending gate cards (CTO schema / design / QA) with approve·deny; CTO decision log |
| **Skills** | explore | "What can this company actually do?" | 44 skills grouped by team, search, on-need (loaded now?) indicator |
| **Build Board** | monitor/act | "What's being built?" | task lanes queued→running→review→done; Linear-synced if wired |
| **Strategy** | explore | "What's the plan?" (founder mode) | strategy/ artifacts: brief · icp · positioning · roadmap · gtm |
| **Fleet** | monitor | "Are the servers up?" (if fleet-manager used) | server cards, health, expose status — read-only |

Nav mirrors the operator's job, not the folder tree.

## 3. Agentic UX patterns (what makes it feel alive)

- **Agent = living card.** Role, status (`idle` dimmed · `working` accent-pulse · `blocked` amber), current task, skill currently loaded, last action + timestamp. Idle agents are visibly dimmed — the **on-need activation** principle made visual.
- **Routing you can see.** When work routes owner → reviewer, draw the hand-off as an edge/animation between the two agent cards. One-owner-one-reviewer rendered, not described.
- **Gates are interactive checkpoints, not log lines.** A pending gate is a card with the verdict action; approving writes `decisions.md` / a verdict file the terminal reads on its next step.
- **The live feed.** Hook events stream in, grouped by team, so you *see* the company working — the difference between an org chart and mission control.
- **Command palette (Cmd/Ctrl-K).** Every slash command (`/onboard`, `/build`, `/fix`, `/schema`, `/design`, `/team`, `/company`), brain switch, and gate action — keyboard-first, terminal-native muscle memory. One-click "copy command" (always) or direct-send (if Remote Control on).
- **Brand-driven re-skin.** Switching the active company re-themes the content surfaces from that brain's `brand{}` tokens — reinforces that one deck runs many companies.

## 4. Visual language

- **Aesthetic:** "command deck" — dark, high-contrast, generous negative space, **one** restrained accent for system chrome (the existing neon-cyan is a fine default). Not a purple-gradient template. Company content uses the active brain's tokens.
- **Layout:** left rail (nav by job) · top status strip (active brain · live/paused · session cost · model) · main canvas (per-view) · right drawer (agent / gate / company detail).
- **Type:** UI sans for prose; **mono** for agent names, skill IDs, file paths, commands, git refs — the terminal-native signal.
- **Density:** Command Deck medium · Activity dense · Brain Studio low.
- **Motion:** 150–250ms; feed items slide in; gate approval quick-and-satisfying; honor `prefers-reduced-motion` (fade, no translate).
- **Tokens:** role-named — `color-surface`, `color-accent`, `agent-idle`, `agent-working`, `gate-pending`, `gate-passed` — light + dark, sourced from the brain when a company is active.

## 5. Component specs (the load-bearing ones)

- **Agent card** — avatar/role · status dot · current task · loaded skill · last-action time. States: idle (dim) / working (pulse) / blocked (amber + reason).
- **Team lane** — team label · member count · roll-up status · expands to its agent cards.
- **Brain panel** — company name · vision one-liner · scope does/doesn't · tone · stack · credential-readiness (env names present? — never values) · `_placeholder`/DRAFT badge.
- **Gate card** — deliverable · owner → reviewer · checklist · **Approve / Request changes** (writes verdict) · links to the artifact.
- **Event feed item** — timestamp · team color · agent · verb (used skill X / edited file Y / handed off to Z) · one-click expand.
- **Stat tile** — value + unit + delta vs last + freshness ("live" / "2m ago"). No bare numbers.
- **Command palette** — fuzzy list of commands/actions; shows the resolved slash command before you run it.

## 6. States (design all of them — per `dashboard-design`)

- **Loading:** skeletons, never a bare spinner.
- **Empty:** name what belongs + the action — "No company yet → run `/onboard` or open Brain Studio."
- **Error:** what failed + retry (e.g., "Couldn't read `companies/` — is the repo path right?").
- **Terminal not live (the special one):** show last-known file state fully, with a calm banner — "Static view. Start `claude` in this repo (hooks on) to go live." When the session + hooks are detected, flip to live automatically.

## 7. Data contract & endpoints

Build on what exists; add three, all local, env-names-only, never secret values:

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/runpack` | GET | structure/state summary *(exists)* |
| `/api/active` | POST | switch active company *(exists)* |
| `/api/brain` | POST | create draft brain + `brain-request.json` *(exists)* |
| `/api/events` | GET (SSE) | tail `.claude/tex-events.jsonl` → live feed *(new)* |
| `/api/gate` | POST | write a gate verdict to `decisions.md` *(new)* |
| `/api/task` | POST | queue a task file the terminal consumes *(new)* |

**Hooks to wire** (in `settings.json`, so the feed has data): `SessionStart`, `PostToolUse` (matcher `*`), `SubagentStart`, `SubagentStop`, `Stop` → each appends a compact JSON event line. Keep payloads to names/paths — no file contents, no secrets.

## 8. Stack

Next.js (existing) + **shadcn/ui** (layout, tables, palette, drawer) + **Tremor** (charts, KPI tiles) — both copy-paste, brandable from brain tokens. `fs.watch` → SSE for live. Zero external network calls (matches the privacy/secrets rule). Port 4100.

## 9. Build phases (ship value early)

1. **Extend what exists** — Command Deck reading `/api/runpack`, brain switch, roster, skills. *(mostly done)*
2. **Go live** — hooks + `.claude/tex-events.jsonl` + `/api/events` SSE + the activity feed and agent-card live status. *(the "agentic" leap)*
3. **Write path** — interactive gates (`/api/gate`), Build Board + `/api/task`, command palette.
4. **Polish** — brand-driven re-skin per company, Strategy + Fleet views, Linear sync, `prefers-reduced-motion`.

## Done-gates (for the design and its build)

- Every view states its intent + question set in a comment; a widget answering none is cut.
- All four states implemented, including **terminal-not-live**.
- Live feed proven with a **real hook** firing (not mocked).
- Content re-skins from the active brain's tokens; zero template-default colors baked in.
- App is `noindex`, localhost-only; the UI never displays a secret value.
- The 5-second test: on the Command Deck, "healthy? / what's happening? / anything need me?" answerable at a glance.
