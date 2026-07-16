---
name: company-onboarding
description: Onboard a new company (or app project) into the Arion runpack. ALWAYS run this before any team does work for a company that has no profile yet. Collects company name, app name, brand assets, DB credentials, n8n credentials, and other config, then builds the company brain that all 52 agents load.
---

# Company Onboarding — Building the Company Brain

Every Arion agent loads a "company brain" before working. This skill creates that brain.
Run it when: the user names a new company/app, `companies/active-company.json` is missing,
or the user asks to switch to a company that has no profile.

## Step 1 — Always ask the onboarding questions

Ask the user (use AskUserQuestion where available, otherwise ask in chat). Never skip,
never invent answers. Ask in groups, not one giant wall:

**Identity**
1. Company name (becomes the slug, e.g. "Acme Labs" → `acme-labs`)
2. App / product name (may differ from company name)
3. One-sentence description of what the product does

**Brain: scope, vision, emotion**
4. Scope — what the company does and explicitly does NOT do
5. Vision — where this is going in 1–3 years
6. Emotion / tone — how the brand should feel (e.g. "premium and calm", "playful and fast",
   "serious and trustworthy"). This drives design, copy, and even code comment style.
7. Target audience — who this is for

**Brand assets**
8. Logo files or links (store files under `companies/<slug>/brand/assets/`)
9. Brand colors (hex values) — primary, secondary, any others
10. Fonts / typography preferences
11. Any existing brand guidelines documents

**Technical config**
12. Database credentials — host, port, database name, user, password, provider
13. n8n credentials — instance URL, API key
14. Other credentials the project needs (Stripe, cloud provider, SMTP, analytics, …)
15. Preferred tech stack (or "let the CTO decide" — then cto + solutions-architect pick
    and record it)

## Step 2 — Store secrets SAFELY (hard rule)

- Raw secret values go ONLY into `.env` at the project root. Create it if missing.
- Ensure `.env` is in `.gitignore` BEFORE writing any secret to it. If not, add it first.
- Name vars with the company slug prefix: `ACME_LABS_DB_HOST`, `ACME_LABS_DB_PASSWORD`,
  `ACME_LABS_N8N_URL`, `ACME_LABS_N8N_API_KEY`, …
- The profile.json stores ONLY the env var names, never the values.
- Never echo secret values back in chat, logs, commits, or generated code.

## Step 3 — Write the company brain

Create `companies/<slug>/profile.json` from `templates/company-profile.template.json`,
filling every field from the answers. Also create:

- `companies/<slug>/brand/brand.md` — brand-designer formalizes colors, type, logo rules
- `companies/<slug>/decisions.md` — empty decision log for cto
- `companies/<slug>/incidents.md` — empty incident/pattern log
- `companies/<slug>/research/` — empty dir for research team output

Then write `companies/active-company.json`:

```json
{ "active": "<slug>", "switched_at": "<ISO date>" }
```

## Step 4 — Data foundation (automatic, with review)

Immediately after the brain exists:

1. **data-engineer** derives the initial data table schema from the product description
   and scope — entities, relationships, full DDL — following the `data-schema-design` skill.
   It designs autonomously; it asks the user only what genuinely cannot be inferred.
2. **cto** reviews the schema against the checklist. CHANGES REQUIRED loops back to
   data-engineer; only APPROVED schemas proceed.
3. On approval, data-engineer applies it: SQL migrations for the configured database,
   and/or n8n data tables via the configured n8n instance if the project uses them.

## Step 5 — Confirm

Report to the user: company brain created at `companies/<slug>/`, which env vars were
registered (names only), schema status (approved/pending), and that all 52 agents will
now operate under this brain. Remind them `/company <name>` switches brains at any time.

## Switching companies

`/company <name>`: if `companies/<slug>/profile.json` exists, update
`active-company.json`. If not, run this onboarding from Step 1. Multiple companies can
coexist; only one is active at a time.
