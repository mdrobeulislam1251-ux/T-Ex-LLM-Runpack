# companies/ — reference seeds (NEVER live brains)

**This directory ships with the runpack git clone. It is read-only reference
material.** The clone is refreshed from GitHub — anything written here is silently
lost — and it is shared by every project, so a brain stored here collides across
projects. Never read a profile from this directory as the active brain; every
profile here is a `"_placeholder": true` DRAFT seed. To use one, COPY it to
`<project-root>/.tex-llm/companies/<slug>/` and complete it with `/onboard <slug>`.

Live brains live in each project's own config root, created by `/onboard`:

```
<project-root>/.tex-llm/companies/
  active-company.json        # which brain is live: {"active": "<slug>"}
  <slug>/
    profile.json             # the brain: scope, vision, emotion, brand, stack, credential refs
    brand/
      brand.md               # formalized brand guidelines (brand-designer)
      assets/                # logos and other brand files
    decisions.md             # CTO decision log (schema/architecture verdicts)
    incidents.md             # incident + failure-pattern log
    research/                # research team output (competitor matrix, briefs)
```

Rules:

- `profile.json` holds credential **env var names only**. Raw secret values live in the
  project's `.env`, which must be gitignored.
- Only one company is active at a time per project; switch with `/company <name>`
  (updates the PROJECT's `.tex-llm/companies/active-company.json`, never this clone).
- Agents never invent brain fields — a missing profile routes to `/onboard`.

## The three planned companies (the outbound engine's three slots)

The three operating companies this runpack is being built to run ship as
`"_placeholder": true` drafts — one per slot of the outbound engine, one specialized
power each:

- **Trusted Leads** (`trusted-leads`) — **List slot**: hyper-personalized lead lists
  via API (ICP-sourced, enriched, verified, send-ready)
- **Lead Gen Jay** (`lead-gen-jay`) — **Mailbox slot**: Inbox Insider,
  high-performance sending infrastructure (domains, auth, warmup, reputation)
- **Consulti AI** (`consulti`) — **Track slot**: everything tracked and ready for the
  next process (stage, status, suppression, next action per contact)

Their DRAFT fields are completed and confirmed by running `/onboard <slug>`; their live
operational skills currently run in the separate `Outbound agent` workspace and are
referenced by name only. No placeholder is active by default. They are **recommended
defaults, not requirements** — the slot is the contract, the tool is swappable: wire
any outbound tool (data source, mailbox stack, CRM/ledger) into a slot by re-pointing
the env var names in the brain's `credentials` section, and teams build against what
is wired.
