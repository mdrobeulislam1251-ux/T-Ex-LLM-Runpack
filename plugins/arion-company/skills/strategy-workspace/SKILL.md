---
name: strategy-workspace
description: Use when the runpack starts in an empty or strategy-less folder, when the user says "start strategy" or names a new venture, or before any dev project brain exists — the strategist leads first, produces strategy artifacts in strategy/, scaffolds the full workspace (dev, marketing, sales, docs, dashboard), then configures the project brains via /onboard and hands off to the teams.
---

# Strategy Workspace — Strategy-First Start

The flow this enables: the user creates a folder, starts a terminal session, calls T-Ex — and T-Ex wakes up as the **strategist**, not as a code generator. Strategy is produced and confirmed FIRST; the workspace and dev brains are configured FROM it; only then do the dev/marketing teams start.

## Trigger

Fire when ANY of: the working folder is empty (or has no `companies/` and no code), the user says "start strategy" / "new venture" / names a company that has no brain, or a build request arrives with zero strategy artifacts. If code already exists → this is Developer mode, run `project-bootstrap` instead.

## The flow

**1. Strategist intake (two questions, that's all)** — same doctrine as `company-onboarding`: the venture's name, and "tell me about it — structure and vision, in your own words". No interrogation; deriving is our job.

**2. Research loop** — run `research-strategy`: research-lead frames the sweeps → market-analyst maps the landscape → product-strategist derives scope/differentiation → content-strategist drafts tone → cto proposes the stack. `product-gtm-strategy` shapes offer, pricing posture, and launch angle.

**3. Write the strategy artifacts** — into `strategy/`, one file each, no empties:

| File | Holds |
|---|---|
| `strategy/brief.md` | Venture in one page: what, for whom, why now, in the user's own words + refinements |
| `strategy/icp.md` | Ideal customer profile — specific enough to DISQUALIFY prospects |
| `strategy/positioning.md` | Category, differentiation, objections, competitor one-liners |
| `strategy/roadmap.md` | Now / next / later — each item with the question it answers |
| `strategy/gtm.md` | Channels, offer, pricing posture, launch sequence |

**4. One confirm pass** — present the strategy as a compact summary; ask a single question: "adjust anything, or lock it in?" Their words always beat our research.

**5. Scaffold the workspace** (after the lock — never before):

```
<workspace>/
  strategy/       # strategy data — strategist owns; teams read, never edit
  dev/            # development server — the product/web-app code
  marketing/      # marketing server — campaigns, content, SEO assets
  sales/          # outbound ops — lists, sequences (created when first needed)
  docs/           # user-supplied architecture & data-model docs
  dashboard/      # dashboard package (user/Grok-built; reads the data contract)
  companies/      # brains — created by /onboard, not by hand
```

```powershell
# PowerShell
'strategy','dev','marketing','docs','dashboard' | ForEach-Object { New-Item -ItemType Directory -Force $_ | Out-Null }
```
```sh
# POSIX
mkdir -p strategy dev marketing docs dashboard
```

Each folder gets a 3-line README stub naming its owner team and what belongs in it — nothing else. Empty scaffolding with 40 boilerplate files is noise.

**6. Configure the dev project brains** — run `/onboard <venture>` now: the strategy artifacts ARE the briefing (pass them in — never re-interview the user for what strategy/ already says). The generated brain must not contradict `strategy/`; where research and strategy disagree, strategy wins and the conflict is flagged in one line.

**7. Hand off** — dev work starts inside `dev/` via `project-bootstrap` (probe, credentials, then build); marketing works in `marketing/` from `strategy/gtm.md` + `strategy/icp.md`; the ecosystem brains (data/verification/sending) are RECOMMENDED defaults the user can swap for their own tools — record the actual choice in the brain's credentials section as env var names.

## Rules

- Strategy data lives ONLY in `strategy/` — one source. Teams read it; change requests route back through the strategist; direct edits by other teams are reverted.
- Every strategy claim that came from research (not the user) carries its evidence or is marked assumption — `research-strategy` kill-criteria apply.
- The strategist does not write product code, and the dev team does not rewrite positioning. Same one-owner rule as everywhere (`orchestration-runpack`).
- Re-entering an existing workspace: read `strategy/` BEFORE proposing anything — contradicting locked strategy without flagging it is a defect.

## Done-gates

- **Strategy start done** = the five artifacts exist with real content, the user locked the direction, the scaffold exists, and at least one brain is configured from it.
- **Strategy change done** = artifact updated + each affected team pinged in one line ("icp narrowed to X — affects targeting in marketing/ and onboarding copy in dev/").
- Never report "strategy done" from generated files alone — the user's explicit lock IS the gate.
