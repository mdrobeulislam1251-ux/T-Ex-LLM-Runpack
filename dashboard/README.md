# T-Ex Command Deck

SaaS-grade control dashboard for the T-Ex LLM 53-agent company runpack. Dark, animated
"modern" UI: aurora backdrop, glass panels, neon team accents, live data read
straight from this repo's files — no separate backend, no database.

## Run it (git-native workflow)

```bash
git clone https://github.com/mdrobeulislam1251-ux/T-Ex-LLM-Runpack.git
cd T-Ex-LLM-Runpack/dashboard
npm install
npm run dev        # → http://localhost:4100
```

Work in Claude Code in the repo root as usual; the deck reflects every change on
refresh (company brains, decision logs, incident logs). Commit and push the
`companies/` changes like any other code.

## Views

| View | What it shows |
|---|---|
| **Overview** | Animated stats, the active company brain, the hard review gates |
| **Teams** | All 9 teams and 53 agents with their specialties, color-coded |
| **Brain Studio** | Create a company from just a name + vision briefing (see below) |
| **Companies** | Every brain in the repo; switch which one is live |
| **Gates & Logs** | The active company's CTO decision log and incident log |

## Brain Studio — smart brain generation

You never fill in brain fields. You type the company name and a free-text briefing
about structure & vision. The deck then:

1. Creates `companies/<slug>/` with a draft `profile.json` — credential env var names
   pre-derived (`<SLUG>_DB_HOST`, `<SLUG>_N8N_API_KEY`, …), values never stored.
2. Writes `brain-request.json` with your briefing.
3. Sets the company active.

Then run `/onboard <name>` in Claude Code: the research team (research-lead,
market-analyst, product-strategist, content-strategist, cto) picks up the request and
**generates** scope, vision, mission, emotion/tone, audience, voice, and stack. You get
one confirm pass. Only credentials (into gitignored `.env`) and brand asset files are
ever asked for — those can't be researched.

## Architecture

- Next.js 14 (app router) + Tailwind. No UI libraries; all effects are CSS.
- `lib/data.ts` reads `../companies`, `../plugins/tex-llm` via `fs` at request
  time (`force-dynamic`), so the deck is always in sync with the repo.
- `POST /api/brain` — creates the draft company + brain request (validates input,
  409 on existing slug).
- `POST /api/active` — switches `companies/active-company.json`.
- Secrets: the dashboard never reads, writes, or displays secret values — only env
  var names.
