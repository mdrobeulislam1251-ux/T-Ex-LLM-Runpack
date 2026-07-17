---
name: company-onboarding
description: Onboard a new company (or app project) into the Arion runpack. ALWAYS run this before any team does work for a company that has no profile yet. The user only provides the company name and what they know about structure & vision — the research team GENERATES the full brain. Only credentials (DB, n8n, other config) and brand asset files are ever asked for directly.
---

# Company Onboarding — Smart Brain Generation

Every Arion agent loads a "company brain" before working. This skill creates that brain.
**The user never hand-fills brain fields.** They know their company and vision; the
research team derives everything else. Run this when: the user names a new company/app,
`companies/active-company.json` is missing, or a `brain-request.json` exists for a
company (created by the Arion dashboard's Brain Studio).

## Step 0 — Check for a dashboard brain request

If `companies/<slug>/brain-request.json` exists, the user already provided their
briefing through the dashboard. Read `company_name` and `user_briefing` from it and
skip straight to Step 2 (do NOT re-ask what they already wrote). Delete the file after
Step 3 completes.

## Step 1 — Ask only what the user actually knows

Two questions. That's the whole interview at this stage:

1. **Company name** (becomes the slug, e.g. "Acme Labs" → `acme-labs`) — and app name
   if it differs.
2. **"Tell me about your company — structure and vision, in your own words."**
   Free text. Whatever they say is the briefing. Do not interrogate them about scope
   documents, tone adjectives, or audience segments — deriving those is OUR job.

## Step 2 — Research team GENERATES the brain

Run the `research-strategy` skill loop on the briefing:

1. **research-lead** frames the briefing into research questions and sweeps: what this
   kind of company is, who its market is, what users of such products expect,
   terminology, comparable companies.
2. **market-analyst** maps the competitive landscape and target-audience reality.
3. **product-strategist** derives: scope (does / does-not), vision (1–3 year), mission,
   and structural differentiation — aligned with, never contradicting, the user's own
   words.
4. **content-strategist** drafts `emotion_tone` and 2–3 `voice_examples` that fit the
   company's market position and the user's phrasing style.
5. **cto** proposes a default tech stack sized for the product (recorded with
   `decided_by: "cto"`), unless the briefing named one.

Fill EVERY brain field in the profile from this work. Empty brain fields after
onboarding are a defect.

## Step 3 — One confirm pass (not a questionnaire)

Present the generated brain to the user as a compact summary: scope, vision, mission,
tone, audience, proposed stack. Ask a single question: "Adjust anything, or lock it
in?" Apply their adjustments verbatim — their words always beat our research.

## Step 4 — Ask ONLY for what cannot be researched

These are the only other things ever asked, because no research can produce them:

- **Brand assets** — logo files/links, brand colors, fonts, existing guideline docs
  (if the user has none, brand-designer generates a starter identity from the brain's
  emotion_tone instead — mark it `generated: true` in brand.md).
- **Database credentials** — host, port, database, user, password, provider.
- **n8n credentials** — instance URL, API key.
- **Other config** the project needs (Stripe, cloud, SMTP, analytics, …).

### Secrets rule (hard)

- Raw secret values go ONLY into `.env` at the project root; create it if missing and
  ensure `.env` is in `.gitignore` BEFORE writing.
- Env var names use the company slug prefix: `ACME_LABS_DB_HOST`,
  `ACME_LABS_N8N_API_KEY`, …
- `profile.json` stores ONLY env var names. Never echo secret values in chat, logs,
  commits, or generated code.

## Step 5 — Write the company brain

Create from `templates/company-profile.template.json`:

- `companies/<slug>/profile.json` — fully filled (brain generated, credentials as env
  var names). If the dashboard already created a draft profile, fill its empty fields
  in place and remove the `brain.generation.status: "pending-research"` marker.
- `companies/<slug>/brand/brand.md` + `brand/assets/`
- `companies/<slug>/decisions.md`, `incidents.md`, `research/` (keep the research
  team's onboarding findings in `research/onboarding-brief.md`)
- `companies/active-company.json` → `{ "active": "<slug>", "switched_at": "<ISO>" }`
- Delete `brain-request.json` if it existed.

## Step 6 — Data foundation (automatic, with review)

1. **data-engineer** derives the initial data table schema from the generated brain
   per the `data-schema-design` skill — autonomously.
2. **cto** reviews against the checklist; loop until APPROVED (logged in decisions.md).
3. On approval, apply: SQL migrations for the configured database and/or n8n data
   tables via the configured n8n instance.

## Step 7 — Confirm

Report: brain generated at `companies/<slug>/` (research-derived, user-confirmed),
env vars registered (names only), schema status, and that all 52 agents now operate
under this brain. `/company <name>` switches brains any time.

## Switching companies

`/company <name>`: if `companies/<slug>/profile.json` exists, update
`active-company.json`. If not, run this onboarding from Step 0. Multiple companies
coexist; one is active at a time.
