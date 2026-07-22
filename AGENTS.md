# T-Ex LLM — Full Company Runpack (agent bridge)

This file makes the runpack usable from ANY agentic client — Cursor, Claude Code, or other agents that read `AGENTS.md`.

## Rules of this workspace (all clients)

1. Read `CLAUDE.md` first — the core engine rules (company brain, zero-laziness, TDD gate, secrets policy) apply regardless of which editor or agent runs the session.
2. The operating doctrine lives in `plugins/tex-llm/skills/<name>/SKILL.md` (44 skills). Before doing specialist work (native app, UI/UX, security, data, DevOps, outbound), open the matching skill file and follow it — the routing map is `plugins/tex-llm/skills/orchestration-runpack/SKILL.md`.
3. Personas live in `plugins/tex-llm/agents/<team>/<role>.md`. One owner per task; teams not routed to the task stay silent.
4. Company context lives in `companies/<slug>/profile.json` (active one named by `companies/active-company.json`). No brain → run onboarding before feature work. Never invent company details.
5. Secrets: values in `.env` only (gitignored); everything else references env var NAMES. Never print or commit secret values.
6. Done = run-verified (build runs, test passes, endpoint answers). Exit code 0 alone is "compiled", not "works".

## Client notes

- **Claude Code**: full experience — commands (`/onboard`, `/build`, `/design`, `/schema`, `/fix`, `/team`, `/company`) come from the plugin (`/plugin install tex-llm@tex-llm`). Works on an Anthropic API key or a Claude Pro/Max subscription login.
- **Cursor / other agents**: no slash commands — follow rule 2 manually: route via `orchestration-runpack`, load the team's skills, respect the gates. The files are plain Markdown/JSON on purpose.
