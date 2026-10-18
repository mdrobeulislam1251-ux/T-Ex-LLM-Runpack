# Design reference: Orbix Studio "Botrix" AI Command Center

Source: https://www.instagram.com/p/DeKYi70DCOx/ (Orbix Studio Dashboard, posted 2026-10-06).
Fetched 2026-10-11. See `source.json` for IDs and retrieval method.

Reference only. Third-party work: use it to inform layout and tone, not to copy
assets or the Botrix brand. Brand tokens for any real build still come from the
active company brain (`.tex-llm/companies/<slug>/profile.json`), per `dashboard-design`.

## Slides

| File | Content |
|---|---|
| `slide-1.jpg` | Full dashboard in a browser frame (the canonical view) |
| `slide-2.jpg` | Zoom, left half: nav, KPI row, Agent Activity chart, Live Activity Feed, Connected tools |
| `slide-3.jpg` | Zoom, right half: Refresh / Filter / Create Agent, KPI row, Server Status cards |
| `slide-4.jpg` | Perspective close-up: KPI bar pulse, Daily/Weekly/Monthly toggles, +24.11% tooltip |
| `slide-5.jpg` | Studio contact promo, not UI |

## Original caption (verbatim)

> Botrix: AI Command Center Dashboard UI with Agent and Server Monitoring
>
> The first thing on the screen is four numbers. 12 automations running, 08 apps connected, 02 active servers and a 98% success rate, each with a small bar pulse underneath.
>
> An AI operator needs to know what's running and whether it's healthy. So the Agent Activity chart sits right below, with a +24.11% peak tag pinned to the line, and Daily, Weekly and Monthly toggles to switch the range.
>
> On the right, Server Status gives each machine CPU, RAM and bandwidth gauges, with Restart, SSH and Scale one tap away. Below it, a live activity feed and connected tools like OpenAI and Stripe each get an on/off toggle.
>
> Orange and violet only show up in the chart lines and gauges. Everything else stays soft cream and quiet.
>
> What We Designed→
> - Light dashboard with top navigation
> - Core metric row with bar pulse
> - Agent activity line chart with peak tooltip
> - Server status cards with gauges and actions
> - Live activity feed with status filters
> - Connected tools list with toggles

## Observed spec (read off the slides)

**Intent** (per `dashboard-design` step 1): Monitor + Act for an AI-ops operator.
Top questions: what is running, is it healthy, what do I do about the unhealthy one.

**Layout** (slide-1, 12-col feel):
- Top bar: logo left, segmented nav pills centre (Dashboard · Agent · APIs · Servers · Activity, active pill is near-black), settings / notifications / avatar right.
- Page header: "AI Command Center" H1 left; Refresh, Filter (ghost pills) and Create Agent (solid dark pill) right.
- KPI row: 4 equal columns separated by hairline dividers, not cards. Big number (2-digit, zero-padded "08", "02"), label under it, a small icon pill top-right, and a bar-pulse sparkline (thin vertical bars, darker cluster in the middle) along the bottom.
- Main grid: ~62/38 split. Left column stacks Agent Activity (line chart, range toggles top-right) over a 2-up row of Live Activity Feed and Connected tools. Right column is Server Status, a vertical list of server cards.
- Chart: three smoothed lines (orange primary, violet secondary, grey tertiary), dashed horizontal gridlines, hatched bands to mark off-peak regions, a vertical orange marker with a floating glass tooltip (big delta "+24,11%" plus a one-line label and a close "x").
- Server card: name + region flag, status chip (Running = green dot on mint; Stopped = red dot on blush), one-line spec (OS · RAM / vCPU), three semicircle gauges (CPU red, RAM orange, Bandwidth violet) with value inside and label below, then three equal action pills (Restart · SSH · Scale; a stopped node gets Start · Configure · Delete, Delete tinted red).
- Live Activity Feed: filter chips (All · Success · Failed · Paused, active chip dark), rows with an icon, agent name, status chip and a chevron.
- Connected tools: logo tile, name + one-line description, right-aligned toggle.

**Color** (sampled from the JPEGs, approximate):

| Role | Hex |
|---|---|
| Canvas (warm cream, subtle gradient) | `#e0e0d8` to `#e8f0e8` |
| Card surface | `#eff1ec` / `#f8f8f8` |
| Text and solid pills | near-black `#1f1f1f` |
| Accent 1, chart line + RAM gauge | orange `#e07c20` to `#e48418` |
| Accent 2, chart line + bandwidth gauge | violet `#4a1ae8` to `#5a3cf0` |
| Danger (CPU gauge, Delete, Stopped) | red `#e34247`, blush bg |
| Success (Running) | green text `#36905a`, mint bg |

Rule the caption states and the pixels confirm: saturated color appears only in
chart strokes, gauge arcs and status chips. Nav, buttons and KPIs are monochrome.

**Type**: geometric sans (Outfit / Urbanist family look). Weights are light for labels,
regular for numbers at ~40px, heading ~32px. Numbers use lining figures.

**Shape**: large radii everywhere (cards ~20px, pills fully rounded), 1px hairline
dividers instead of borders on the KPI row, soft blurred shadow only on the tooltip.

## Relevance to this repo

Maps onto the T-Ex Command Deck Overview view: the KPI row + bar pulse fits "active
company / teams / agents / gates", the Server Status card pattern fits fleet hosts
from `server-fleet-management`, and the Live Activity Feed fits decision and
incident logs. The current deck is dark/aurora (`dashboard/README.md`); this
reference is the light-mode counterpoint and is NOT a directive to switch themes.
