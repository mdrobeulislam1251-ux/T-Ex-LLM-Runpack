# companies/

Each subdirectory is one company brain, created by `/onboard`:

```
companies/
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
- Only one company is active at a time; switch with `/company <name>`.
- Agents never invent brain fields — a missing profile routes to `/onboard`.
