---
name: data-schema-design
description: The mandatory workflow for designing data table schemas — data-engineer designs autonomously from the company brain, cto reviews against a hard checklist, and only APPROVED schemas get applied to databases or n8n data tables. Use for any table, migration, warehouse, or n8n data table design.
---

# Data Schema Design — Design, Review Gate, Apply

The user should NOT have to hand-design tables. The data-engineer derives the schema from
the company brain and the product requirements, and the cto guarantees quality. This
skill defines that loop.

## Phase 1 — Derive (data-engineer)

1. Read the company brain: product description, scope, target audience, multi-tenancy,
   compliance notes, tech stack (which database engine).
2. Read the PRD / feature request if one exists.
3. Extract entities, relationships, and lifecycle: what is created, by whom, what state
   transitions exist, what gets queried most.
4. Ask the user ONLY questions that genuinely cannot be inferred (e.g. "do deleted
   records need to be recoverable?" when compliance is unclear). Everything else, decide.

## Phase 2 — Design (data-engineer)

Produce the complete design in one document:

- **Entity map**: each table, its purpose, its relationships (a mermaid ER diagram).
- **Full DDL** for the brain's database engine, including:
  - Primary keys (UUIDv7 or bigint identity — pick and justify)
  - Foreign keys with explicit ON DELETE behavior per relation
  - NOT NULL / CHECK / UNIQUE constraints — enforce integrity in the database
  - `created_at` / `updated_at` (timestamptz) on every table; soft-delete strategy stated
  - Indexes for every predicted frequent query, each justified in a comment
  - Naming: snake_case, singular or plural chosen once and applied everywhere
- **Multi-tenancy**: if the brain says multi-tenant, tenant_id on every tenant-owned
  table + row-level security policies in the DDL.
- **Migration plan**: ordered, reversible migration files, not one blob.
- **n8n data tables**: if workflows need them, the equivalent table definitions to create
  via the configured n8n instance (credentials referenced from .env by name).
- **Seed data**: minimal seed script for development.

## Phase 3 — CTO review gate (MANDATORY, no bypass)

The cto reviews against this checklist and returns a verdict:

- [ ] Every relationship has correct cardinality and FK with deliberate ON DELETE
- [ ] No missing constraints the application would otherwise have to enforce
- [ ] Index set matches the stated query patterns — no unindexed hot path, no dead indexes
- [ ] Multi-tenant isolation complete (tenant_id + RLS) if applicable
- [ ] PII identified; encryption/masking noted where the brain's compliance requires
- [ ] Naming consistent with the company's convention
- [ ] Migrations reversible and safe on a non-empty database (lock awareness)
- [ ] No secrets or environment-specific values inside DDL
- [ ] Scales to the brain's 12-month growth expectation without redesign

Verdict: **APPROVED** / **CHANGES REQUIRED** (numbered items → back to Phase 2) /
**REJECTED** (wrong approach; reason and direction stated). Log the ruling in
`companies/<slug>/decisions.md` with the date.

## Phase 4 — Apply (data-engineer + database-engineer)

Only after APPROVED:

1. Write migration files into the project (e.g. `migrations/` or the ORM's format).
2. Apply to the development database using credentials from `.env` (referenced by env
   var name; values never appear in code or output).
3. Create n8n data tables via the n8n API where the design includes them.
4. Run the seed script; verify with a smoke query per table.
5. Production application is a separate step, executed by database-engineer with a
   backup taken first.

## Hard rules

- No schema is applied anywhere — not even dev — without a logged CTO APPROVED.
- Schema changes after approval re-enter the gate as a delta review.
- Credentials: env var references only. If `.env` lacks the vars, stop and route to
  `company-onboarding` to collect them properly.
