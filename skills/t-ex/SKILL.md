---
name: t-ex
description: T-ex multi-team agent workspace. Use when user says @T-ex, @T-ex ops/sales/dev, domain review, team dashboard, personal BD agent, or tex CLI.
triggers:
  - "@T-ex"
  - "@tex"
  - t-ex
  - tex workspace
  - domain review
  - personal bd
---

# @T-ex — multi-team agent workspace

You are operating **T-ex LLM** workspace. Same SQLite DB as the web UI: `.texllm/workspace.db`.

## Call patterns

| User says | Action |
|-----------|--------|
| `@T-ex …` or `tex @T-ex …` | CEO/workspace orchestrator goal |
| `@sales …` / `tex @sales …` | Run **sales** team flow |
| `@ops` `@dev` `@tech` `@ceo` `@fulfillment` | That team’s flow |
| `@personal-bd` or BD ask | Personal business development agent |
| Domain / website URL to review | `tex review <domain>` |

## Shell (preferred)

```bash
# list teams
tex teams

# team dashboard JSON
tex dash sales

# run agentic flow for a team
tex run ops "Stabilize onboarding SLA"
tex @sales "Draft 5 cold emails for SaaS founders"

# domain → ideas + brains + skills (shared DB)
tex review example.com --notes "B2B logistics"

# personal BD agent
tex bd "Map 3 partnership paths for our agent platform"

# add brain / skill
tex brain sales "Closer" --role closer --prompt "Qualify and close"
tex skill dev "PR checklist" --description "Review PR quality"
```

If `tex` not on PATH:

```bash
python3 -m texllm.tex_cli teams
python3 -m texllm.tex_cli run ceo "Weekly priorities"
```

## Web

Open host (default port 3006) → **Workspace**, **Teams**, **Domain review**, **Personal BD**.

## Rules

1. Prefer `tex` CLI for durable writes (ideas/brains/skills) so UI sees them.
2. Connect Claude first (`docs/CLAUDE-FIRST.md`) for real model output.
3. Custom customer teams: `POST /v1/workspace/teams` or create via UI.
4. Do not invent team slugs — run `tex teams` first.
