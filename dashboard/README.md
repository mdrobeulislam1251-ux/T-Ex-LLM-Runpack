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
| **Run Ops** | Dispatch a team run to the runtime host and watch the real result land (see below) |
| **Teams** | All 9 teams and 53 agents with their specialties, color-coded |
| **Brain Studio** | Create a company from just a name + vision briefing (see below) |
| **Companies** | Every brain in the repo; switch which one is live |
| **Gates & Logs** | The active company's CTO decision log and incident log |

## Run Ops — the deck actually commands now

Pick a runtime team, state a goal, dispatch. The deck queues the run on the T-Ex
runtime host (`POST /v1/workspace/teams/{slug}/run-async` via the server-side proxy
`/api/run`) and polls the job live. **Code mode** drives a headless coding agent on
the host that edits files for real — the result panel shows the workdir, the files
changed, and the diff. **Draft mode** returns a reviewed text answer only.

Wire it up in `dashboard/.env.local` (env var *names* only — never commit values):

```bash
TEX_RUNTIME_URL=http://127.0.0.1:3006   # where `python -m texllm.cli serve` runs
TEX_RUNTIME_API_KEY=                     # only if the host sets HOST_API_KEY
```

If the host is down, Run Ops shows an offline state with the exact start command —
it never fakes a run. Code mode additionally needs the `claude` CLI on the *host*
machine; missing CLI fails the job with a clear error instead of returning prose.

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
- `POST /api/run` + `GET /api/run?id=…|?teams=1` — server-side proxy to the runtime
  host for run dispatch / job polling / team list (`TEX_RUNTIME_URL`,
  `TEX_RUNTIME_API_KEY`); the browser never holds the host key.
- Secrets: the dashboard never reads, writes, or displays secret values — only env
  var names.
