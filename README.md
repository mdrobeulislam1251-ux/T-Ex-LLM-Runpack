# T-Ex LLM — The Full Company Runpack

*(repo: T-Ex-LLM-Runpack — the single combined version of the agent product.
The former `T-Ex-LLM-Agent` and `T-ex-LLM` repos are merged in here with full
history — see `launcher/` and `runtime/` — and are archived.)*

**One repo, three distribution modes:**

1. **Plugin mode** (this runpack) — the 53-agent company inside Claude Code:
   `/plugin install tex-llm@tex-llm`, driven by the per-project company brain.
2. **Standalone launcher** (`launcher/`) — one portable T-Ex agent (dev + ops +
   strategy persona) launched via `launcher/launch-tex.ps1` from any project;
   skills mirror `plugins/tex-llm/skills/` at every launch.
3. **Runtime host** (`runtime/`) — the self-hosted Python product: FastAPI host +
   React operator console on port 3006, Company Runbook spine (Intent → Deploy),
   multi-provider auth, agent-CLI detect/spawn, `tex` workspace CLI.

A **company-in-a-box** for terminal AI sessions: **53 specialist agents in 9 teams backed
by 44 deep doctrine skills**, driven by a switchable **company brain** (scope, vision,
emotion/tone, brand, stack, credentials). Install it into any project and the AI works
like a full company — with hard review gates so the output is accurate, not improvised.

One rule shapes everything here: **one specialty, deeply mastered**. Every agent owns
exactly one discipline — and every outside capability T-Ex leans on fills exactly one
slot (lead lists, mailboxes, tracking, …). Specialists and specialist tools don't
overlap; the orchestrator combines them into one engine.

**Two modes, one runpack:**

- **Founder mode** — build a sellable product from scratch, strategy-first: T-Ex wakes
  as the **strategist** (`strategy-workspace`), locks direction with you, scaffolds the
  workspace (`strategy/ dev/ marketing/ docs/ dashboard/`), then `/onboard` → PRD →
  architecture → schema (CTO gate) → design → build → QA → ship → launch.
- **Developer mode** — join ANY existing codebase as the dev team: `project-bootstrap`
  probes the stack and live-verifies every credential first, then delivers doc-by-doc.
  You share design/architecture docs (data models included); the team builds against
  them — schema changes always pass the CTO gate.

## Why

AI coding alone drifts: wrong assumptions, half-finished code, no reviews. T-Ex LLM fixes
that structurally:

- **Specialists, not generalists** — each task goes to an agent whose whole prompt is
  that discipline. Outside tools are held to the same bar: one slot, one specialized
  power, combined by the orchestrator instead of overlapping.
- **A changeable brain** — one profile per company defines what everything should sound
  like, look like, and run on. Switch companies, and all 53 agents switch with it.
- **Hard gates** — the data engineer designs schemas autonomously, but **nothing is
  applied until the CTO approves**. UI doesn't ship past the design director. Fixes
  don't close without regression tests.
- **Zero-laziness engineering** — no pseudocode, no `// rest of code here`, TDD enforced.

## Install

This repo is a Claude Code **plugin marketplace**. In any project:

```
/plugin marketplace add mdrobeulislam1251-ux/T-Ex-LLM-Runpack
/plugin install tex-llm@tex-llm
```

Then start with:

```
/onboard YourCompanyName
```

## Run it from anywhere (terminal-first)

- **Claude Code on a Max/Pro subscription**: run `claude`, sign in once — no API key needed.
- **Claude Code on API billing**: set `ANTHROPIC_API_KEY` in the environment instead.
- **Cursor / other agents**: the runpack is plain Markdown/JSON — `AGENTS.md` at the repo
  root routes any agent through the same skills and gates (no slash commands there; the
  files are the product).
- **Linear**: `claude mcp add --transport sse linear https://mcp.linear.app/sse` connects
  project management; the `linear-integration` skill maps build/fix cycles to issues and
  moves an issue to Done only after run-verification.

## Runpacks for external agents

`runpacks/` holds operating docs and design specs:

- `runpacks/grok-dashboard-builder.md` — a complete runpack for a **Grok** agent building
  dashboards for this workspace: the guaranteed data contract (repo file paths +
  `GET /api/runpack`, `POST /api/active`, `POST /api/brain`), segment/intent design
  doctrine, and run-verified done-gates.
- `runpacks/tex-llm-dashboard-design.md` — the **design vision** for the T-Ex LLM
  dashboard: an agentic command deck that directly drives and reflects the local
  terminal (the read / live-hooks / write bridge), views by intent, agentic UX patterns,
  component specs, and a phased build plan.
- `runpacks/grok-tex-web-brand-builder.md` — a full build spec for a **Grok** agent to
  build T-Ex LLM's **own** premium web presence standalone: marketing site (3D hero, live
  animated workflow, MCP/API/integrations, pricing, API docs, press/social kit), the SaaS
  app dashboard (agentic kanban board, checklists, team directory, billing), and the brand
  kit — with shadcn/Tremor/Framer-Motion/R3F stack, performance + accessibility guardrails,
  and a clean data seam that wires into T-Ex once confirmed.

The dashboard package itself is the user's (or Grok's) responsibility — T-Ex LLM
guarantees the endpoints and access.

## The Command Deck (dashboard)

A SaaS-grade visual dashboard ships in [`dashboard/`](dashboard/): dark animated
modern UI showing the active brain, all 9 teams / 53 agents, review gates, and the
CTO decision + incident logs — read live from the repo files.

```bash
cd dashboard && npm install && npm run dev   # → http://localhost:4100
```

Runs on any computer with Node.js ≥ 18 (`winget install OpenJS.NodeJS.LTS` on Windows /
`brew install node` on macOS). Clone the repo on that machine, run the two commands,
open the browser — the deck reads the live repo files next to it.

Its **Brain Studio** creates companies from nothing but a name and a vision briefing —
see the next section.

## Smart brain generation (you never fill in the brain)

You provide only what you actually know: the **company name** and a free-text
**briefing about structure & vision** — via `/onboard` in Claude Code or the
dashboard's Brain Studio. The research team (research-lead, market-analyst,
product-strategist, content-strategist, cto) then **generates** the full brain: scope,
vision, mission, emotion/tone, target audience, voice examples, and a proposed stack.
You get one confirm/adjust pass.

Only two things are ever asked for directly, because they can't be researched:

1. **Brand asset files** — logos, colors, fonts (or brand-designer generates a starter
   identity from the tone)
2. **Credentials** — database, n8n, other config → stored **only** in gitignored
   `.env`; `.tex-llm/companies/<slug>/profile.json` stores env var **names**, never values

Right after the brain is confirmed, the **data-engineer** derives the initial table
schema by itself and submits it to the **CTO** for mandatory review — you don't
hand-design tables.

## Commands

| Command | What it does |
|---|---|
| `/onboard [name]` | Name + vision briefing → research team generates the brain → schema → CTO review |
| `/company [name]` | Show the active brain, or switch/create another company |
| `/build <feature>` | Full pipeline: PRD → architecture → schema → design → build → QA → ship → docs |
| `/design <thing>` | Design pipeline: research → flows → visuals → motion → tokens → handoff |
| `/schema [change]` | Data engineer designs/evolves schema; CTO gate; apply to DB / n8n data tables |
| `/fix <bug>` | Issue loop: triage → root-cause fix → regression test → prevention |
| `/team [task]` | Show the 53-agent roster, or route a task to the right owner |

## The outbound engine (three slots, one power each)

When work is outbound — filling pipeline for the active company — T-Ex runs an
**outbound engine** built on the same doctrine as the roster: **one specialized power
per slot**, nothing overlapping. Three slots make the engine, and **three planned
companies hold them** — the operating companies this runpack is being built to run:
**Trusted Leads**, **Consulti AI**, and **Lead Gen Jay**, each specializing in
exactly one slot:

| Slot | The one thing it does | Planned company (placeholder brain) |
|---|---|---|
| **List** | Hyper-personalized lead lists — ICP-sourced, enriched, verified, send-ready via API | **Trusted Leads** (`trusted-leads`) |
| **Mailbox** | High-performance sending infrastructure — domains, auth, warmup, reputation; mail that lands | **Inbox Insider** by Lead Gen Jay (`lead-gen-jay`) |
| **Track** | Everything tracked and ready for the next process — every contact's stage, status, next action | **Consulti AI** (`consulti`) |

Alone, each is one power. Combined, they are a pipeline: the **List** slot feeds the
**Mailbox** slot, outcomes land in the **Track** slot, and the Track slot stages the
next process — while the roster (SDR, email specialist, data engineer, CTO gate)
operates the machine under the `b2b-outbound-pipeline` doctrine.

**A capability spine, not a bundle.** The slot is the contract; the tool is swappable.
Wire Apollo or Clay into List, your own warmed Google-Workspace + sequencer stack into
Mailbox, any CRM into Track — the brain's `credentials` env-var names record what's
actually wired, agents build against what IS wired (never what's recommended), and
every gate and threshold in `b2b-outbound-pipeline` applies identically whatever fills
the slots. The three planned companies ship as pre-wired placeholder SEED brains in the runpack's
own `companies/` directory (reference material only — never loaded in place);
`/onboard <slug>` copies a seed into your project's `.tex-llm/companies/<slug>/` and
completes it there when its turn comes. Their live operational skills currently
run in the separate `Outbound agent` workspace (cold-email suite, consulti-scrape,
lead-tracking-db, …); porting + scrubbing them into this repo is a planned cycle.

## The 53-agent roster

**Executive (4):** ceo-orchestrator · cto · cpo · coo

**Engineering / Dev (12):** engineering-manager · fullstack-polyglot (65 languages) ·
frontend-engineer · backend-engineer · mobile-engineer · api-engineer ·
database-engineer · data-engineer · devops-engineer · sre-engineer · security-engineer ·
performance-engineer

**Design (7):** design-director · ux-researcher · ux-designer · ui-designer ·
design-system-engineer · brand-designer · motion-designer

**AI (6):** ai-lead · ai-developer · prompt-engineer · ml-engineer · rag-engineer ·
ai-eval-engineer

**Issue Fixers (5):** triage-lead · bug-hunter · hotfix-engineer · regression-tester ·
root-cause-analyst

**Technical (7):** solutions-architect · integration-engineer (n8n) · cloud-engineer ·
platform-engineer · qa-automation-engineer · technical-writer · **fleet-manager**
(multi-server SSH + identity docs + environment setup)

**Marketing (5):** marketing-director · content-strategist · seo-specialist ·
social-media-manager · email-marketing-specialist

**Sales (4):** sales-director · sales-development-rep · account-executive ·
customer-success-manager

**Research & Strategy (3):** research-lead · market-analyst · product-strategist

## Skills (the doctrine each team runs on)

**44 deep skills** — the 7 runpack skills plus the full T-Ex craft library (20 portable,
run-verified playbooks), the six per-platform native skills + Avalonia cross-platform
desktop, and ten new forges
(`native-app-delivery`, `ui-ux-design`, `app-security`, `linear-integration`,
`dashboard-design`, `strategy-workspace`, `server-fleet-management`,
`server-identity-builder`, `fleet-app-hosting`, `agent-environment-setup`). The per-team
mapping lives in `orchestration-runpack` → "Team skill libraries"; teams not routed to a
task stay silent.

### Fleet hosting (local SSH)

The fleet-manager works with your **local `~/.ssh/config`** — no cloud API. It routes an
app to the right box by role + capacity, deploys over SSH (docker compose / systemd / pm2
/ static), and exposes it the **right way**: app on `127.0.0.1`, one front door (reverse
proxy or outbound tunnel) with TLS, the database never public. Your fleet is described in
`fleet-registry.json` — copy `templates/fleet-registry.example.json` and fill it locally;
the real file is **gitignored**, only the placeholder ships (same for `ssh-config.example`).

| Layer | Skills |
|---|---|
| Runpack core | `company-onboarding`, `orchestration-runpack`, `fullstack-65`, `data-schema-design`, `design-core`, `issue-fix-loop`, `research-strategy` |
| Behavior core | `environment-recon`, `execution-discipline`, `verification-gates`, `project-bootstrap` |
| Dev | `api-design`, `fullstack-delivery`, `systematic-debugging`, `app-security`, `ui-ux-design`, `dashboard-design` |
| Native apps | `native-app-delivery`, `android-dev`, `ios-dev`, `macos-dev`, `windows-dev`, `linux-dev`, `harmony-dev`, `avalonia-dev` (cross-platform desktop) |
| Data engineering | `postgres-patterns`, `supabase-platform`, `sql-analytics`, `elasticsearch-opensearch`, `clickhouse-analytics`, `data-pipelines` |
| Ops / DevOps | `server-ops-safety`, `network-diagnosis`, `docker-operations`, `grafana-observability`, `devops-cicd` |
| Fleet / SSH / environment | `server-fleet-management`, `server-identity-builder`, `fleet-app-hosting`, `agent-environment-setup` |
| Strategy / GTM | `product-gtm-strategy`, `b2b-outbound-pipeline`, `strategy-workspace` |
| Integrations | `linear-integration` |

## Review gates (hard, non-negotiable)

| Deliverable | Gate |
|---|---|
| Data schemas, migrations, n8n data tables | **cto** — checklist verdict, logged |
| Architecture, stack changes, security-sensitive work | **cto** |
| All design output before engineering | **design-director** |
| UI implementation before merge | **design-system-engineer** (spec fidelity) |
| AI features / prompt changes | **ai-eval-engineer** (eval numbers) |
| Bug fixes | **regression-tester** (test added + suites green) |
| Releases | **engineering-manager** + **qa-automation-engineer** |

## Repository layout

```
.claude-plugin/marketplace.json      # marketplace manifest
plugins/tex-llm/
  .claude-plugin/plugin.json
  agents/<team>/<role>.md            # the 53 agents
  skills/<skill>/SKILL.md            # the 44 doctrine skills
  commands/*.md                      # /onboard /company /build /design /schema /fix /team
dashboard/                           # T-Ex Command Deck (Next.js) — npm run dev
templates/company-profile.template.json
companies/                           # placeholder SEED brains (reference only — live brains: <project-root>/.tex-llm/companies/)
runpacks/                            # operating docs for external agents (Grok dashboard builder)
launcher/                            # standalone portable T-Ex agent (merged from T-Ex-LLM-Agent)
runtime/                             # self-hosted FastAPI host + React console (merged from T-ex-LLM)
CLAUDE.md                            # core engine rules for this repo
```

## Git-native workflow

Clone the runpack for the dashboard and reference material. Real work happens in YOUR
project directory: `/onboard` there creates `<project-root>/.tex-llm/companies/`, and
the brain versions with the project's own repo — never commit brains into the runpack
clone (it is refreshed from GitHub and shared by every project):

```bash
git clone https://github.com/mdrobeulislam1251-ux/T-Ex-LLM-Runpack.git
cd T-Ex-LLM-Runpack/dashboard && npm install && npm run dev   # the deck
# ...meanwhile use Claude Code in YOUR project directory: /onboard, /build, /fix ...
# in your project repo:
git add .tex-llm/ && git commit -m "brain updates" && git push
```

## Security model

- `.env` is the only home for secret values, and it is gitignored.
- Profiles, code, logs, and chat reference secrets by env var name only.
- The dashboard never reads, writes, or displays secret values — env var names only.
- Database and n8n access always flows through those references.
- The security-engineer reviews auth and secrets handling; the CTO gates anything
  credential-adjacent.
