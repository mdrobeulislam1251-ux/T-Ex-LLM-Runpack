---
description: Have the data-engineer design (or evolve) the data schema, with mandatory CTO review
---

Run the `data-schema-design` skill for: $ARGUMENTS

data-engineer derives entities and full DDL autonomously from the active company brain
and any PRD — asking the user only what cannot be inferred. cto reviews against the
checklist; only APPROVED schemas are applied (dev database migrations and/or n8n data
tables, credentials referenced from `.env` by name).

If $ARGUMENTS is empty, design the initial schema for the active company's product.
If credentials are missing from `.env`, route to `/onboard` to collect them properly.
Log the CTO verdict in `companies/<slug>/decisions.md`.
