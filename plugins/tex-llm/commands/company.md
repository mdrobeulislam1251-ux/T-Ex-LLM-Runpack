---
description: Switch the active company brain, or show the current one
---

Company brain control. $ARGUMENTS is the company name (or empty).

- No arguments: read `.tex-llm/companies/active-company.json` and the active profile; report the
  active company's name, app, scope, vision, tone, and configured credential references
  (env var NAMES only — never values).
- With a name: slugify it. If `.tex-llm/companies/<slug>/profile.json` exists, update
  `.tex-llm/companies/active-company.json` to that slug and confirm the switch, summarizing the
  newly active brain. If it does not exist, run the `company-onboarding` skill for it.

All 53 agents follow whichever brain is active — a switch changes scope, vision, tone,
brand, stack defaults, and credential references everywhere at once.

Path anchor (hard rule): `.tex-llm/` resolves at the PROJECT root — the directory
this session started in. If `<project-root>/.tex-llm/companies/` is missing,
create it first. Never read or write the runpack/plugin clone's own `companies/`
directory — its profiles are `_placeholder` seeds (copy in, never load in place),
and a profile with `"_placeholder": true` is never an active brain.
