---
description: Switch the active company brain, or show the current one
---

Company brain control. $ARGUMENTS is the company name (or empty).

- No arguments: read `companies/active-company.json` and the active profile; report the
  active company's name, app, scope, vision, tone, and configured credential references
  (env var NAMES only — never values).
- With a name: slugify it. If `companies/<slug>/profile.json` exists, update
  `companies/active-company.json` to that slug and confirm the switch, summarizing the
  newly active brain. If it does not exist, run the `company-onboarding` skill for it.

All 53 agents follow whichever brain is active — a switch changes scope, vision, tone,
brand, stack defaults, and credential references everywhere at once.
