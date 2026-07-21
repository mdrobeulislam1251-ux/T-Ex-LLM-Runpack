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
