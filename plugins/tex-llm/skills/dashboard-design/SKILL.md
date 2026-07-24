---
name: dashboard-design
description: Use for any product dashboard or analytics UI — choosing the view type by audience intent (monitor / analyze / act / report / portal), segment-specific layouts, anti-generic-template rules that stop the "fake app" feel, the SEO split between public pages and the app, and the open-source component stack. Brand specifics come from the company brain; visual craft from ui-ux-design.
---

# Dashboard Design — Segment & Intent Based

A dashboard is an answer machine: it exists to answer a named set of questions for a named audience in seconds. The #1 failure mode is shipping "the AI dashboard template" — one generic dark-purple admin view for every product. B2B customers smell it instantly, and it reads as a fake app. This skill prevents that structurally.

## Step 1 — Name the intent BEFORE any layout

Every view gets exactly one intent. Write the audience + their top 3–5 questions first; the layout follows from the table:

| Intent | Audience question | Refresh | Density | Layout pattern | Exclude |
|---|---|---|---|---|---|
| **Monitor** | "Is it healthy right now?" | live / ≤60s | high | Status tiles top, alert list, time-series grid below | historical deep-dives, vanity KPIs |
| **Analyze** | "Why did X change?" | on-load | medium | Filters left/top, one primary chart, drill-down table | autoplaying widgets, alerts |
| **Act** (operate) | "What do I do next?" | live | medium | Work queue front and center, one-click actions, detail drawer | charts that don't change a decision |
| **Report** (exec) | "Are we on track?" | daily/weekly | LOW | 5–7 KPIs vs target with trend, one narrative line each | raw tables, live tickers, >7 numbers |
| **Portal** (customer-facing) | "What's my status / value?" | on-load | LOW | Plain-language summary, their data only, next-step CTA | internal jargon, dense grids, other tenants' shapes |

One page = one intent. "Monitor + analyze + report on one screen" is how the generic template happens.

## Step 2 — Segment profiles (starting layouts)

- **Exec / founder KPI**: 5–7 KPIs max, each with target + delta vs last period. Weekly grain. If a number has no owner and no target, it's decoration — cut it.
- **Sales / CRM**: pipeline funnel by stage, activity queue (who to touch today), win-rate trend. The queue is the product; charts are context.
- **Marketing / outbound**: campaign table (sent → delivered → opened → replied → booked), channel mix, cost per meeting. Funnel stages must reconcile (`sql-analytics` gates).
- **Ops / internal metrics**: route to `grafana-observability` — don't hand-build what Grafana does better. Hand-build only customer-visible or product-specific ops views.
- **Product analytics**: retention cohort matrix, feature-adoption funnel, segment filter. Approximate counts labeled as such.
- **Customer portal**: the trust surface. Brand-first, fewer numbers, plain words ("3 campaigns running, 41 replies this week"), visible freshness ("updated 2 min ago"), and an obvious next action. This is the view that convinces customers the product is real.

## Anti-generic rules (the fake-app killers)

1. **Brand from the company brain, always** — colors/typography/tone from `.tex-llm/companies/<slug>/profile.json` + brand.md, applied as tokens (`ui-ux-design`). Template defaults (indigo-on-dark, glassmorphism, purple gradients) only if the brand actually says so.
2. **Real data wired from day one.** No hardcoded numbers, no `Math.random()` demo series. A metric that never changes across visits is how users decide the app is fake. If data isn't ready: honest empty state, not invented numbers.
3. **Write the question set into the code** — a comment block atop each view listing audience + questions. A widget answering none of them gets deleted in review.
4. **Kill decorative widgets**: world maps with 3 dots, fake activity feeds, circular progress for unbounded metrics, weather. Every pixel answers a question or leaves.
5. **Navigation mirrors the user's job** (Campaigns / Leads / Replies / Billing), not your database tables.
6. **Every number carries context**: unit, comparison baseline (vs last period / vs target), and freshness timestamp. A bare "1,284" is noise.
7. **All four states designed**: loading = skeletons (not spinner-only), empty = what belongs here + the action to create it, error = what happened + retry, partial = show what loaded, flag what didn't.

## The SEO / credibility split (public vs app)

The "breaks SEO and customers think fake app" failure is one architectural mistake: shipping the app shell as the public site.

- **Public marketing pages** (landing, pricing, blog): separate surface, SSR/SSG (static where possible), real `<title>`/meta description/OG image/structured data per page, fast LCP (< 2.5s), crawlable HTML. Never a client-rendered SPA shell — crawlers and buyers both bounce.
- **The app/dashboard**: behind auth, `noindex` (`X-Robots-Tag: noindex` or meta), on an app path or subdomain (`app.` / `/app`). It should never appear in search results.
- **Product proof on public pages** = screenshots/short video of the REAL dashboard with real-shaped data — not a stock mockup. Buyers recognize stock dashboards.
- Verify the split: `curl.exe -sSI "$APP_URL/app" | grep -i x-robots` shows noindex; view-source of the landing page shows real content without JS.

## Chart choice (fast table)

| Question shape | Chart |
|---|---|
| Trend over time | line / area (y from zero for area) |
| Compare categories | horizontal bar, sorted |
| Composition | stacked bar; donut only ≤ 5 slices |
| Funnel / stages | ordered bars with stage-to-stage % |
| Retention | cohort matrix (triangle) |
| Distribution | histogram |
| Single status | stat tile with delta + spark line |

Never: 3D anything, dual-axis without explicit labels, pie charts with 10 slices, gauges for unbounded values.

## Component stack (open-source, copy-paste ownership)

Default React stack: **Next.js + shadcn/ui (layout, forms, tables) + Tremor (charts, KPI cards, 35+ dashboard components)** — both copy-paste-into-repo libraries, so the code is owned, brandable, and has no lock-in. Recharts sits underneath Tremor when raw control is needed.

- Admin/CRUD-heavy internal tools: Refine or plain shadcn tables + server actions.
- BI/exploration for analysts: buy-not-build — Metabase / Superset pointed at the warehouse.
- Internal ops/infra: Grafana (`grafana-observability`).
- Aesthetic direction: pick ONE design family per brand (the awesome-design-md DESIGN.md approach — a named aesthetic with tokens), record the choice in the company brain, and reuse it everywhere. Mixing families per page = template smell.

## Done-gates

- **View done** = renders LIVE data, all four states implemented, brand tokens applied (zero template default colors), the view's question set answerable in a 5-second scan, and freshness visible.
- **Dashboard done** = every view passed above + auth verified on app routes + `noindex` verified on app surface + public pages pass Lighthouse SEO ≥ 90 with real meta/OG.
- **Credibility check** = show it to someone who knows the segment: if they ask "is this a template?", it failed — re-apply the anti-generic rules.
