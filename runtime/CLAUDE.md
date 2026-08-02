# T-Ex LLM — Claude Code entry

When the user mentions **@T-ex**, **@tex**, **T-ex**, or team agents (ops/sales/dev/tech/ceo/fulfillment/personal-bd), load and follow:

- `skills/t-ex/SKILL.md`

## Quick commands

```bash
tex teams
tex dash sales
tex run dev "Ship release notes agent"
tex run dev --code "Add /healthz endpoint"   # real edits + diff (claude CLI required)
tex review customer-domain.com
tex bd "Growth plan for Q3"
tex @T-ex "What should CEO prioritize this week?"
```

Claude-first auth: `docs/CLAUDE-FIRST.md`  
Workspace product: `docs/WORKSPACE.md`

## Two kinds of "brain" — never mix them

- **Company brains** (repo root `CLAUDE.md` rule 0): JSON profiles at
  `<project-root>/.tex-llm/companies/` of whatever project a session runs in. Docs and
  skills OUTSIDE `runtime/` mean this when they say "brain".
- **Workspace brains** (`tex brain`, `docs/WORKSPACE.md`): rows in this runtime's SQLite
  workspace DB — product data of the T-ex host, exportable to `firmware/` packages.
  Everything INSIDE `runtime/` means this.

Never write a company-brain profile into the workspace DB, and never store
workspace-brain content as a `.tex-llm/companies/` profile.
