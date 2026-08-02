# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Sections 0–5 are the T-Ex LLM core engine rules (behavioral doctrine — they govern how work is routed and gated). Sections 6–7 are the developer reference for this repo itself. The `runtime/` subproject carries its own `CLAUDE.md` — read it before touching anything under `runtime/`. Cross-client rules for Cursor and other agents live in `AGENTS.md`.

## 0. Company Brain First
- **Brain resolution (hard rule):** every brain lives in the PROJECT's config root —
  `<project-root>/.tex-llm/companies/` — where `<project-root>` is the directory the
  session was started in. Before any team does work: read
  `.tex-llm/companies/active-company.json`, then the active
  `.tex-llm/companies/<slug>/profile.json`. If `.tex-llm/` does not exist, bootstrap it
  (create `.tex-llm/companies/`) before anything else. Never resolve `companies/`
  against a parent directory, the home directory, or the runpack/plugin clone.
- **The runpack clone is read-only reference.** The `companies/` directory shipped in
  this repo (and its plugin-marketplace clone under `~/.claude/plugins/`) holds
  `_placeholder` seeds only. Never read one as a live brain and never write there —
  the clone is refreshed from GitHub (writes are silently lost) and is shared by every
  project (brains would collide). To start from a seed, COPY it into the project's
  `.tex-llm/companies/<slug>/` and complete it with `/onboard`.
- A profile with `"_placeholder": true` is not a brain — route to `/onboard` instead of
  working from its DRAFT fields. No brain → run the `company-onboarding` skill
  (`/onboard`) and always ask the user the onboarding questions (app name, brand assets,
  DB credentials, n8n credentials, other config). Never invent company details.
- Brains are project-scoped: two projects may hold the same slug; they are independent
  files — never merge, sync, or symlink them across projects.
- Disambiguation: the runtime host's workspace "brains" (`runtime/` — `tex brain`,
  SQLite rows) are that product's own data, NOT company brains. Neither kind is ever
  written into the other's store (see `runtime/CLAUDE.md`).
- Route all work through the `orchestration-runpack` skill: one owner, one reviewer,
  hard gates (schemas → cto, design → design-director, fixes → regression-tester).
- Before working, the owning agent loads its team's skill library (the "Team skill
  libraries" table in `orchestration-runpack`) — skills carry the doctrine, agent files
  carry the persona. Teams not routed as owner or reviewer of the task stay silent.

## 1. Zero-Laziness Enforcement
- Partial code and templates are forbidden. Write fully realized, compilation-ready
  code blocks.
- When editing a file, rewrite or safely block-replace the target sections completely.
  Never truncate with comments like `// rest of code here`.
- **Full-run agentic**: a routed task runs to its done-gate in one continuous run —
  probe instead of guessing, no mid-task questions outside the Ask-first gates
  (`execution-discipline` → Full-Run Rule), and any required ask is batched into one.
  Review gates run agent-to-agent; the user sees verdicts, not permission requests.

## 2. Test-Driven Development (TDD) Gate
- No production feature code without an associated failing test first.
- Every milestone task executes a localized shell test command before it is declared
  complete.

## 3. Secrets Policy
- Secret values live only in `.env` (gitignored). Profiles and code reference env var
  names only. Never print, log, or commit secret values.

## 4. Remote Verification Architecture
- Server-side interactions are routed securely using whatever remote-access method the
  active company brain configures (`tech.remote_access` in its profile) — e.g. plain
  SSH, a bastion host, or a mesh VPN profile such as Tailscale. Nothing is hardcoded
  to any specific host or VPN; if a company has no remote_access configured, work
  locally.
- Use headless Playwright automation checkpoints to visually verify frontends or
  external API state loops.

## 5. Operating Modes & Inputs
- **Founder mode** (sellable product from scratch) is strategy-first: the
  `strategy-workspace` skill wakes the strategist, locks direction with the user,
  scaffolds `strategy/ dev/ marketing/ docs/ dashboard/`, THEN `/onboard` creates the
  brain → PRD → architecture → schema (CTO gate) → design → build → QA → ship → launch.
- **Developer mode** (any existing codebase): run the `project-bootstrap` skill first —
  probe the stack, live-verify every credential, at most one batched ask — then deliver
  doc-by-doc against the user's specs.
- **User-supplied architecture / data-model docs are first-class input**: store them under
  `.tex-llm/companies/<slug>/research/` (or the project's docs folder), route schema work through
  `/schema` (data-engineer → cto gate), and never redesign what a doc already decides
  without flagging the conflict in one line.
- **Clients**: Claude Code in a terminal session (Anthropic API key or Claude Max/Pro
  login) is primary; Cursor and other agents follow `AGENTS.md`. Project management syncs
  through the `linear-integration` skill — issues reach Done only after run-verification.
- **External dashboards**: the guaranteed read surface is the data contract in
  `runpacks/grok-dashboard-builder.md` (repo files + `GET /api/runpack`,
  `POST /api/active`, `POST /api/brain`, and run dispatch via `POST /api/run` +
  `GET /api/run?id=…` proxied to the runtime host). External agents write only inside
  `dashboard/` and never read `.env`. Dashboard craft rules live in the
  `dashboard-design` skill.
- **Messaging channels** (runtime host): Telegram / WhatsApp / Google Chat / iMessage-via-
  BlueBubbles / custom-HMAC webhooks dispatch team runs from chat (`run dev --code fix X`
  → ack + completion pushed back). Default-deny sender allowlists, platform-native webhook
  verification, `tex channels poll telegram` needs no public URL — `runtime/docs/CHANNELS.md`.
  Distinct from the outbound engine's List/Mailbox/Track slots below.
- **Server fleet**: multi-server SSH work routes to the fleet-manager
  (`server-fleet-management` + `server-identity-builder`), read/observe by default,
  state-changing work through `server-ops-safety`. Secrets on servers stay as PATHS —
  never read a server secret file into output. New-machine provisioning (Context7 + other
  MCPs, git identity, SSH aliases, portable manifest) is `agent-environment-setup`.
- **The outbound engine is three slots, one specialized power each** — mirroring the
  one-specialty-per-agent doctrine: **List** (hyper-personalized lead lists; default
  Trusted Leads API), **Mailbox** (high-performance sending infra; default Inbox
  Insider by Lead Gen Jay), **Track** (everything tracked, ready for the next process;
  default Consulti AI). Defaults are recommended, never forced — any outbound tool fills
  a slot; the brain records the user's actual tools as env var names, and teams build
  against what is wired, not what is recommended (`b2b-outbound-pipeline` → "The Engine
  Slots").

## 6. Commands (per surface — nothing builds at repo root)

```bash
# Dashboard — T-Ex Command Deck (Next.js 14 + Tailwind, port 4100)
cd dashboard && npm install && npm run dev      # dev server on :4100
npm run build && npm run start                  # production
npm run lint

# Runtime host — FastAPI + team runners (Python ≥3.9)
cd runtime && bash scripts/setup.sh --port 3006 --non-interactive   # one-time: .venv, editable install, web build
set -a && source .env && set +a && source .venv/bin/activate
python -m texllm.cli serve                      # host API + web console on :3006
pytest                                          # all tests (needs the .venv; config in pyproject.toml)
pytest tests/test_runner.py -k <expr>           # single file / single test
python -m texllm.cli agents                     # detect terminal AI CLIs on PATH
tex run dev --code "goal"                       # code mode: real edits + diff artifacts (needs claude CLI)

# Runtime web console (React 19 + Vite, served from runtime host)
cd runtime/apps/web && npm install && npm run dev
npm run build                                   # tsc --noEmit typecheck + vite build → dist/ served by host

# Plugin (no build step — Markdown/JSON + one Node hook)
#   install into a Claude Code session: /plugin install tex-llm@tex-llm
cd plugins/tex-llm && node hooks/chat-capture.mjs --dry-run --transcript <sample.jsonl>   # chat-brain harness

# Launcher — portable standalone mode (macOS/Linux; PowerShell twin exists)
bash launcher/launch-tex.sh
```

## 7. Repo map & architecture

| Surface | What it is |
|---|---|
| `plugins/tex-llm/` | THE product: marketplace plugin — 53 agents in 9 teams, 44 skills, 7 slash commands, chat-brain hook |
| `dashboard/` | Command Deck UI + the external-agent API contract (`/api/runpack`, `/api/active`, `/api/brain`) |
| `runtime/` | Self-hosted multi-agent host: FastAPI + SQLite workspace + React console + firmware packages (own docs, tests, CLAUDE.md) |
| `launcher/` | Portable standalone Claude Code home (`.claude-tex/`) |

- **Plugin anatomy**: `agents/<team>/<role>.md` = persona only; `skills/<name>/SKILL.md` = the doctrine (routing map: `skills/orchestration-runpack/SKILL.md`); `commands/*.md` = `/onboard /company /build /design /schema /fix /team`; `hooks/` + `migrations/` = the chat-brain. The plugin version lives in BOTH `plugins/tex-llm/.claude-plugin/plugin.json` and root `.claude-plugin/marketplace.json` (`metadata.version`) — always bump them in sync.
- **Chat-brain hook** (`plugins/tex-llm/hooks/chat-capture.mjs`, registered for the `Stop` event in `hooks/hooks.json`): on every completed turn it extracts the turn from the transcript, redacts secret shapes, appends to the running project's `.claude/chat-log.jsonl` (always; 1000-turn bound, cursor-deduped) and best-effort POSTs to a DB when `CHATBRAIN_DB_URL`/`CHATBRAIN_DB_KEY` (or Supabase env fallbacks) are set — table from `migrations/arion_chatlog.sql`. Hard contract: it never throws and always exits 0; never "improve" it in a way that can throw or block a turn.
- **Launcher mirrors skills**: `launcher/launch-tex.sh` rsyncs `plugins/tex-llm/skills/` into `launcher/.claude-tex/skills/` on every launch. Edit skills ONLY in the plugin — the launcher copy is generated, and `.claude-tex/` is gitignored except its `CLAUDE.md` and `settings.json`.
- **`runtime/` is a subproject on purpose**: own `pyproject.toml` (console scripts `tex`, `t-ex`, `texllm`, `texllm-host`, `texllm-run`, `texllm-serve`), own docs (`runtime/docs/QUICKSTART.md`, `AUTH.md`, `WORKSPACE.md`, `CHANNELS.md`, `architecture.md`), playbooks for external agents, and unit tests in `runtime/tests/`. `texllm/channels/` = messaging-channel adapters (base contract + registry; third-party adapters self-register via `CHANNEL_PLUGINS`). Provider resolution is Claude-CLI-first, then API keys, then mock. Its SQLite "workspace brains" are not company brains (§0).
- **Firmware lifecycle** (runtime): workspace teams/brains/skills live in SQLite (7 seeded teams) → `tex export <team>` (or `POST /v1/workspace/teams/{slug}/export-firmware`) generates `firmware/<team>-agents/` — manifest.yaml with the four runner roles (planner/executor/reviewer/integrator) plus a prompt file per brain → team runs (`tex run <team> "goal"`) prefer that package and fall back to `firmware/sample-assistant` → `TeamRunner` executes plan → draft/review retry loop → integrate, under the manifest's iteration/retry limits. In **code mode** (`tex run <team> --code`, or `mode:"code"` on `/run`, `/run-async`, `/v1/jobs`) the executor stage instead drives a headless `claude -p` session in a per-run workdir (`.texllm/runs/<job-id>/` git-inited, or `--workdir` in place) — the reviewer reviews the real diff and the result carries `workdir`/`files_changed`/`diff`; no claude CLI → the job fails clearly, never silently drafts prose (`texllm/workers/code_executor.py`). Everything the runtime touches (`.env`, `firmware/`, `.texllm/workspace.db`, `.texllm/credentials.json`) resolves against the CWD the host/CLI starts in — one directory = one workspace.
- **Reference-only directories**: `companies/` = `_placeholder` seed brains; `templates/` = copyable configs (company profile, fleet registry, n8n, agent-runner, statusline); `runpacks/` = operating contracts for external agents (Grok dashboard/brand builders, web-dev pipeline); `scripts/linear-bootstrap.sh` = Linear PM seeding.
- **CI**: the only workflows are Claude Code review/mention actions (`.github/workflows/claude-code-review.yml`, `claude.yml`) — there is no test/build CI; run-verification happens locally per the TDD gate.
