# Arion Core Engine Rules

## 0. Company Brain First
- Before any team does work: read `companies/active-company.json`, then the active
  `companies/<slug>/profile.json`. No brain → run the `company-onboarding` skill
  (`/onboard`) and always ask the user the onboarding questions (app name, brand assets,
  DB credentials, n8n credentials, other config). Never invent company details.
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
  `companies/<slug>/research/` (or the project's docs folder), route schema work through
  `/schema` (data-engineer → cto gate), and never redesign what a doc already decides
  without flagging the conflict in one line.
- **Clients**: Claude Code in a terminal session (Anthropic API key or Claude Max/Pro
  login) is primary; Cursor and other agents follow `AGENTS.md`. Project management syncs
  through the `linear-integration` skill — issues reach Done only after run-verification.
- **External dashboards**: the guaranteed read surface is the data contract in
  `runpacks/grok-dashboard-builder.md` (repo files + `GET /api/runpack`,
  `POST /api/active`, `POST /api/brain`). External agents write only inside `dashboard/`
  and never read `.env`. Dashboard craft rules live in the `dashboard-design` skill.
- **Server fleet**: multi-server SSH work routes to the fleet-manager
  (`server-fleet-management` + `server-identity-builder`), read/observe by default,
  state-changing work through `server-ops-safety`. Secrets on servers stay as PATHS —
  never read a server secret file into output. New-machine provisioning (Context7 + other
  MCPs, git identity, SSH aliases, portable manifest) is `agent-environment-setup`.
- **Ecosystem defaults are swappable**: Consulti / Trusted Leads / Lead Gen Jay are
  recommended, never forced — the brain records the user's actual tools as env var names,
  and teams build against what is wired, not what is recommended.
