---
name: research-strategy
description: The Research & Strategy team's method — framing questions, multi-source sweeps, competitive analysis, and turning findings into decision-ready strategy. Use before major product, market, or technical bets.
---

# Research & Strategy — Evidence Before Bets

The company does not bet on vibes. Before major decisions, this loop produces findings
with confidence levels and strategy with kill criteria.

## 1 — Frame (research-lead)

- Convert the vague ask into answerable questions: "should we build X?" becomes
  "who has this problem, what do they use today, what would make them switch, what
  would it cost us to serve them?"
- State the decision at stake and what answer would change it. Research without a
  decision attached is entertainment.

## 2 — Sweep (research-lead, fan out as needed)

Multi-modal by default — one search angle never finds everything:

- Web search: the market, the players, the terminology users actually use
- Competitor materials: pricing pages, docs, changelogs, job postings (they reveal roadmaps)
- Community sentiment: reviews, Reddit/HN/forums — what users complain about is the gap
- Data sources available to the session (scraping tools, datasets) where relevant

Rules: separate **fact** (verifiable) / **claim** (someone says) / **speculation**
(inference). Label confidence high/medium/low per finding. Contradictions get chased,
not averaged.

## 3 — Analyze (market-analyst)

- Competitor matrix: features, pricing, positioning, weaknesses-from-reviews —
  maintained in `.tex-llm/companies/<slug>/research/competitors.md`.
- Market sizing with shown math: TAM/SAM/SOM and every assumption listed.
- Pricing landscape: where the company's packaging fits, where the gaps are.

## 4 — Strategize (product-strategist)

- Score opportunities against the brain: strategic fit with vision/scope FIRST, market
  size second. A big market outside the vision is a distraction, not an opportunity.
- Identify structural differentiation: what competitors can't copy quickly, and why.
- Frame each recommended bet as: expected upside / cost / risk / **kill criteria**
  (what observable result would prove this wrong and end the bet).

## 5 — Deliver

Brief format (to cpo / ceo-orchestrator):

1. Question asked and decision at stake
2. Findings (with confidence + sources)
3. Implications for THIS company (through the brain's lens)
4. Recommendation — one primary option with reasoning, alternatives listed briefly
5. Kill criteria and review date

"We couldn't verify X" is a legitimate, stated finding. Overstated certainty is a
defect in the deliverable.
