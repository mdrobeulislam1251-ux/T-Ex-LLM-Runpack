---
name: product-gtm-strategy
description: Use when the task involves defining who a product sells to, picking a sales motion, setting first-pass pricing, instrumenting a conversion funnel, or deciding whether a launch or new segment is validated enough to spend money scaling it.
---

# Product & GTM Strategy — Operational

Go-to-market as an executable checklist, not a slide deck. Every framework below is fillable in one working session. Output of this skill is always a written artifact in the project (ICP doc, funnel spec, pricing sheet, validation log) — never advice floating in chat.

## The Two Iron Rules

1. **ONE ICP + ONE motion at a time.** One named customer profile, one primary acquisition motion. Every other segment and channel is explicitly parked in writing. Running three motions at 30% effort each produces zero learnable signal; running one at 100% produces a verdict.
2. **20 real prospects before any scale spend.** No paid ads, no SDR hire, no launch-week PR until the exact message has been tested on 20 real, named prospects and hit the scale threshold (protocol below). Scaling an untested message just buys expensive proof that it doesn't convert.

## Step 0 — Probe the Real Product State (never assume)

Before any strategy work, establish what already exists in the repo. Run from the project root.

POSIX:

```sh
grep -rEli 'posthog|mixpanel|amplitude|segment|plausible|heap|gtag' --include='*.js' --include='*.ts' --include='*.tsx' --include='*.py' --include='*.rb' . | head -5
grep -rEli 'stripe|paddle|lemonsqueezy|chargebee|paddle_' --include='*.js' --include='*.ts' --include='*.py' --include='*.env.example' . | head -5
find . -maxdepth 3 -iname '*pricing*' -not -path '*/node_modules/*' | head -5
```

PowerShell:

```powershell
Get-ChildItem -Recurse -Include *.js,*.ts,*.tsx,*.py -Exclude node_modules |
  Select-String -Pattern 'posthog|mixpanel|amplitude|segment|plausible|gtag' -List |
  Select-Object -First 5 Path
Get-ChildItem -Recurse -Include *.js,*.ts,*.py,*.env.example -Exclude node_modules |
  Select-String -Pattern 'stripe|paddle|lemonsqueezy|chargebee' -List | Select-Object -First 5 Path
Get-ChildItem -Recurse -Filter '*pricing*' | Where-Object FullName -NotMatch 'node_modules' | Select-Object -First 5 FullName
```

Findings drive the plan: analytics wired = instrument the 5 metrics now; billing wired = pricing changes are a config task, not a project; neither = instrumentation goes on the launch gate list before anything else.

## 1. ICP Definition — the 6 Fields That Matter

An ICP doc missing any field is incomplete — especially disqualifiers, which is where most ICP docs are fake. Fill all six or don't claim you have an ICP.

| Field | What it must contain | Test of a good answer |
|---|---|---|
| Firmographic | Industry, headcount range, geography, stack/platform | You could build a filterable list in Apollo/Clay from it |
| Trigger event | The observable event that makes them buy NOW | It's detectable from outside (job post, funding, incident, regulation date) |
| Pain | What it costs them today, in hours or currency | Contains a number, not an adjective |
| Current alternative | What they do about it right now (incl. "nothing/spreadsheet") | You can name why it fails them in one sentence |
| Buyer role | Economic buyer AND day-to-day champion, by job title | Two titles, not "the company" |
| Disqualifiers | Who looks like a fit but must be refused | At least 3 concrete exclusions |

Worked B2B example (product: cloud-cost anomaly alerts):

- **Firmographic:** B2B SaaS, 20–200 employees, AWS-primary, raised Seed/Series A in the last 18 months.
- **Trigger event:** monthly AWS bill crossed ~$25k, or finance flagged a >30% month-over-month spike, or first platform-engineer job posting went up.
- **Pain:** cost spikes surface 2–3 weeks late via finance; each late catch wastes $5k–15k; an engineer burns ~2 days/month on manual Cost Explorer archaeology.
- **Current alternative:** AWS Cost Explorer checked ad hoc + a spreadsheet; fails because nobody owns looking at it daily.
- **Buyer role:** economic buyer = VP Engineering; champion = platform/DevOps lead.
- **Disqualifiers:** GCP/Azure-primary; cloud spend under $10k/mo (pain too small); dedicated FinOps team exists (they buy enterprise suites); agencies managing client accounts.

## 2. Motion Selection by Price Point

The motion is not a preference — it's forced by unit economics. Fully-loaded human selling time must fit inside the deal's first-year gross profit.

| Monthly price | Motion | CAC logic |
|---|---|---|
| Under ~$100/mo | Self-serve only (PLG, content, SEO, community) | ACV ≤ $1.2k. One SDR-touched deal costs $750–1,500 fully loaded — a single human touch can exceed year-one revenue. CAC ceiling ≈ $300–500; only automated channels fit under it. |
| ~$100–1k/mo | Sales-assist (self-serve signup + human demo/close on request) | ACV $1.2k–12k. A demo plus two follow-ups ≈ $150–400 of AE time; payback stays under 12 months as long as humans touch only hand-raisers, never cold volume. |
| Above ~$1k/mo | Outbound sales (SDR prospecting + AE close) | ACV $12k+. Full outbound cost per closed deal runs $3k–10k (SDR + AE + tools); it only pays back inside 12–18 months at ACV ≥ ~$10–15k. Below that, outbound is structurally unprofitable no matter how good the reps are. |

Rules: price point sets the ceiling motion, not the floor — a $500/mo product may still self-serve. Mixed pricing across tiers → pick the motion for the tier the ICP actually buys. Changing motion later is allowed; running two primaries at once is not (Iron Rule 1).

## 3. Funnel Instrumentation — Define BEFORE Launch

Five metrics, each with a written definition, a query/dashboard, and a named owner before the first campaign runs. "We'll add analytics after launch" = launch gate failure.

| # | Metric | Definition to write down | Honest B2B SaaS range |
|---|---|---|---|
| 1 | Visitor → signup | Unique visitors to signup completions, per source | 1–5% on relevant traffic; 2% is normal. Below 1% = promise or traffic problem, not a button-color problem |
| 2 | Signup → activated | % reaching the **explicit activation event** within 7 days | 20–40%. If yours is 60%+, the event is probably too weak |
| 3 | Activated → paying | % of activated accounts converting to paid within 30 days | Freemium: 5–15% of activated. Trial w/ card upfront: 40–60%. Opt-in trial, no card: 15–25% |
| 4 | Churn | Monthly logo churn, paid accounts | SMB 3–7%/mo, mid-market 1–2%/mo, enterprise <1%/mo. SMB above 7% = ICP or product problem |
| 5 | Payback months | CAC ÷ (monthly price × gross margin) | <6 excellent, <12 good for self-serve/SMB, 12–18 acceptable sales-assist, >24 broken unless enterprise NRR >120% |

**Activation event rule:** it must be the moment the user first receives the core value — not "completed onboarding", not "logged in twice". For the worked example above: *first anomaly alert delivered on the customer's real cloud account*. Write the event name into the ICP doc and verify it fires: perform one test signup yourself and confirm the event appears in the analytics tool's live-event view. No fired event = metric 2 and 3 are fiction.

## 4. The 20-Prospect Validation Protocol

Run before any scale spend (Iron Rule 2). Prospects must match ALL six ICP fields — padding the list with near-fits invalidates the test.

**What to send** (per prospect, manually, no sequencer for this test):

- Under 90 words, 3 parts: (1) one line proving you saw their trigger event, (2) the pain hypothesis + your promise with a number ("teams like yours find cloud spikes 2–3 weeks late; we alert within the hour"), (3) ONE question as the CTA ("worth 20 minutes?"). No links in the first touch, no attachments.
- One bump after 3–4 business days ("any reaction to the below?"). Nothing after the bump.
- Window closes 10 business days after the last first-touch send.

**What counts as signal — score honestly:**

| Counts (signal) | Does NOT count |
|---|---|
| Meeting booked | Open/click tracking data |
| Reply engaging the problem — including objections and "we already use X" | "Sounds interesting, keep me posted" |
| Forwarded to a colleague ("looping in our platform lead") | Polite decline, LinkedIn like, newsletter signup |

Objections ARE signal: they prove the pain was worth arguing about. Polite interest is the null result dressed up.

**Decision rule after the window closes:**

- **SCALE** — ≥3 meetings booked, or ≥5 substantive replies: message validated; turn on the chosen motion with budget.
- **ITERATE** — 1–2 meetings or 2–4 substantive replies: change exactly ONE variable (the pain named, the promise number, or the buyer role targeted — never all three), rerun with 20 fresh prospects.
- **KILL** — 0 meetings and ≤1 substantive reply: this ICP+message pair is dead; write it into the parked list with the result and pick a different pain or a different ICP. Three consecutive KILLs across different pairs = stop marketing and question the product itself.

## 5. Pricing First Pass

**Value metric first.** The unit price scales on must (a) grow as the customer gets more value, (b) be predictable enough for the buyer to budget, (c) be measurable by your product. Candidates: seats, usage units, monitored volume (e.g., cloud spend under management). Test: "what does the customer get more of as they pay more?" — if the answer is "nothing", the metric is wrong.

**3-tier structure rules:**

- Middle tier = the ICP tier: priced for the ICP doc's buyer, carries the target price point. Design this one first.
- Bottom tier: removes the "too expensive to try" objection and absorbs the below-disqualifier crowd; capped hard on the value metric.
- Top tier: 3–5× the middle price; anchors the middle as reasonable and catches outsized accounts. Gate tiers with the value metric plus 1–2 capability gates (SSO, audit logs, priority support) — never by crippling the core feature.
- Name tiers by buyer ("Starter / Team / Scale"), not metals.

**The two classic failures — reject on sight:**

1. **Cost-plus pricing** ("infra costs $X per account, so charge 3×X"). Price against the value delivered versus the current alternative: quantify what the pain costs (ICP field 3), charge 10–20% of it. The worked example's pain is $5k–15k per late catch — that supports $300–800/mo, regardless of what the servers cost.
2. **Unlimited-everything flat tier.** The largest customer pays the same as the smallest: negative-margin whales, zero expansion revenue, and net revenue retention mathematically capped at 100% minus churn. Every tier gets a value-metric cap.

**Payback sanity check — run it, don't estimate it in your head.** Plug in estimated CAC, monthly price of the ICP tier, and gross margin (default 0.80 for SaaS if unmeasured):

POSIX:

```sh
CAC=1200; PRICE=400; MARGIN=0.80
awk -v c=$CAC -v p=$PRICE -v m=$MARGIN 'BEGIN { pb=c/(p*m); printf "payback: %.1f months -> %s\n", pb, (pb<=18 ? "PASS" : "FAIL (>18mo)") }'
```

PowerShell:

```powershell
$CAC = 1200; $Price = 400; $Margin = 0.80
$pb = $CAC / ($Price * $Margin)
"payback: {0:N1} months -> {1}" -f $pb, $(if ($pb -le 18) { "PASS" } else { "FAIL (>18mo)" })
```

Output `payback: 3.8 months -> PASS` clears the gate; a FAIL means raise the price, cut the CAC channel, or change motion — not "launch anyway and fix later".

## 6. Launch Gate Checklist

All items pass or the launch waits. Each is binary — no "mostly done".

- [ ] ICP doc exists in the repo with all 6 fields filled; disqualifiers list has ≥3 entries.
- [ ] Exactly one motion named as primary; parked segments/channels listed in writing with a revisit date.
- [ ] Activation event named, implemented, and verified fired via a real test signup (event visible in the analytics tool).
- [ ] All 5 funnel metrics have a written definition, a live query/dashboard, and a named owner.
- [ ] 20-prospect protocol completed with a SCALE verdict — an ITERATE or KILL verdict blocks the gate.
- [ ] Pricing page shows a value metric and 3 capped tiers; no unlimited flat tier anywhere.
- [ ] Payback model computed with real numbers: estimated CAC ÷ (monthly price × gross margin) ≤ 18 months.

## Funnel Triage — Reading → Diagnosis → Fix

| Funnel reading | Diagnosis | Fix |
|---|---|---|
| Visitor→signup <1% on ICP-relevant traffic | Promise unclear or wrong audience arriving | Rewrite the hero to the ICP pain sentence verbatim; audit traffic sources against firmographics |
| Signup→activated <15% | Activation too far from signup, or onboarding friction | Cut steps between signup and first value; instrument drop-off per onboarding step |
| Activated→paying <4% (freemium) | Free tier gives away the value metric | Move the value metric behind the paywall; free tier keeps a taste, not the meal |
| Many replies, no meetings | Pain is real, promise not believed | Add a proof number or named mechanism to the promise; shrink the ask to 15 minutes |
| Meetings happen, nothing closes | Champion in the room, economic buyer absent | Requalify on ICP field 5; ask "who signs?" in meeting one |
| Churn >7%/mo (SMB) | Disqualified customers got in anyway | Enforce disqualifiers at signup/sales; churn interviews on the last 5 losses before building anything |

## Forbidden Moves

- NO scale spend (ads, SDR hires, PR) before a SCALE verdict — Iron Rule 2 has no exceptions for "we're confident".
- NO second ICP or second motion "on the side" — parked means parked, in writing.
- NO metric defined after launch, and NO activation event that isn't the product's core value moment.
- NO cost-plus pricing and NO unlimited flat tier — reject both on sight, including in existing pricing pages you're asked to extend.
- NO counting polite interest as validation signal — meetings and objections only.
