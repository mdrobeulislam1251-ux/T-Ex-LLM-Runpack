---
name: b2b-outbound-pipeline
description: Use when building or running B2B cold outbound — sourcing/enriching/verifying lead lists, setting up sending domains and warmup, writing or sending cold-email sequences, or diagnosing bounces, spam placement, or dead reply rates.
---

# B2B Outbound Pipeline

Operational playbook for cold outbound that produces replies without burning a domain. Two rules override everything else in this file: **no list is delivered and no email is sent without the count-and-preview gate**, and **verification always happens before sending, never after**. Domains die in days and recover in weeks — every threshold below exists because crossing it is cheaper to prevent than to repair.

## The Engine Slots (resolve before any stage work)

T-Ex runs outbound as an engine of **three capability slots — one specialized power per
slot**, mirroring the one-specialty-per-agent doctrine. Combined, they are the pipeline:
List feeds Mailbox, Mailbox outcomes land in Track, Track stages the next process.

| Slot | The one thing it does | Powers |
|---|---|---|
| **List** | hyper-personalized lead lists: ICP-sourced, enriched, verified, send-ready | stages 1-5 |
| **Mailbox** | high-performance sending infrastructure: domains, auth, warmup, reputation | stage 6 + section 3 |
| **Track** | pipeline system of record: stage/status/next action per contact, suppression, metrics | stage 7 + all three gates |

Resolve what fills each slot in this order — **the slot is the contract, the tool is
swappable**:

1. **What the brain wires.** The active `companies/<slug>/profile.json` `credentials`
   env-var names are the truth. Build against what IS configured.
2. **What the project shows.** Sequencer/CRM/config files and API keys referenced by
   env var name (section 0 probes). Never guess.
3. **Ecosystem defaults — offer only when a slot is empty and the user asks for a
   recommendation:** Trusted Leads API (List), Inbox Insider by Lead Gen Jay (Mailbox),
   Consulti AI (Track). Recommended, never forced, never presented as the only option —
   Apollo/Clay/Sales Navigator fill the List slot equally; a warmed Google-Workspace +
   sequencer stack fills Mailbox; any CRM or ledger DB fills Track. Every gate and
   threshold below applies identically whatever fills the slots.

## 0. Probe Before Acting

Never assume where the lead data lives or what shape it is in. Locate and measure it first.

```powershell
# PowerShell — find candidate list files and count rows
Get-ChildItem -Recurse -Include *.csv,*.xlsx -File | Select-Object FullName, Length, LastWriteTime
(Import-Csv .\leads.csv).Count            # row count (header excluded)
(Import-Csv .\leads.csv)[0].PSObject.Properties.Name   # column names
```

```sh
# POSIX — same probes
find . -name '*.csv' -o -name '*.xlsx' | head -20
awk 'END{print NR-1}' leads.csv           # row count (header excluded)
head -1 leads.csv                         # column names
```

Also probe: which sequencer/CRM the project actually uses (config files, API keys referenced by env var NAME only), and which domain is configured as the sender — read it from project config, never guess.

## 1. Pipeline Stages

Run stages strictly in order. Each stage has an exit criterion; skipping one shows up later as bounces or spam placement.

| # | Stage | Tooling category | Example tools | Exit criterion |
|---|---|---|---|---|
| 1 | Define ICP | filters, not prose | your CRM's won-deal analysis | ICP written as filter values: industry, headcount range, titles, geo, trigger signal |
| 2 | Source | B2B database / signal scraper | Apollo, Clay, LinkedIn Sales Navigator, Ocean.io | raw list pulled with the ICP filters applied — **count reported before any pull is delivered** |
| 3 | Dedupe + suppress | spreadsheet/CLI diff, CRM match | Clay, dedupe scripts (below) | 0 duplicates by email AND by domain+full-name; 0 matches against the suppression list |
| 4 | Enrich | waterfall enrichment | Clay (waterfall), Apollo, Hunter, Prospeo | ≥90% of rows have first name + company + a personalization field; rows below bar are cut, not guessed |
| 5 | Verify | email verification API | NeverBounce, ZeroBounce, MillionVerifier | every address tagged valid / invalid / catch-all / unknown, dated |
| 6 | Sequence | sending platform | Smartlead, Instantly, Lemlist, Apollo sequences | sequence loaded, suppression re-checked, count-and-preview gate passed |
| 7 | Reply handling | shared inbox / CRM | the CRM the project already uses | every reply classified within 24h; SLA in section 5 |

Dedupe check, both shells:

```powershell
Import-Csv leads.csv | Group-Object email | Where-Object Count -gt 1 | Select-Object Name, Count
```

```sh
cut -d, -f1 leads.csv | sort | uniq -d | head    # adjust -f to the email column
```

## 2. Email Verification Doctrine

- **Hard-bounce budget: <2% per batch.** Gmail/Microsoft score the sending domain on bounce rate; sustained ≥2% degrades reputation, ≥5% commonly triggers blocklisting. One unverified list can do this in a single day.
- **Freshness rule: verified <30 days ago, or verify again.** B2B addresses decay ~2-3% per month (job changes). A "verified" tag without a date is not verified.
- **Never send to `invalid`.** No exceptions, no "it's probably fine", no CEO addresses grandfathered in.
- **Catch-all (accept-all) handling.** SMTP verification cannot confirm these addresses; the domain accepts everything. Policy:
  - Use a verifier with a risky/catch-all tier (MillionVerifier-class) and expect 1-5% of catch-alls to bounce anyway — those bounces count against the 2% budget.
  - Cap catch-alls at ≤20% of any batch, or route them through a secondary sending domain so a bad day doesn't touch the primary.
  - Prefer catch-all rows where enrichment confidence is high (pattern confirmed by another employee's verified address at the same domain).
- **`unknown` = `invalid`** unless a second verifier upgrades it. Two verifiers disagreeing = treat as the worse result.
- Ordering is non-negotiable: source → dedupe → enrich → **verify** → sequence. Verifying after sending starts is an incident report, not a workflow.

## 3. Deliverability Setup — Checklist

Complete ALL items before the first cold send. Each is checkable; check it, don't trust it.

1. **Separate sending domain — never the main domain.** Buy a close variant (`try<company>.com`, `get<company>.com`, `<company>hq.com`). The main domain must be unburnable. Set a redirect from the sending domain to the main site.
2. **SPF** — exactly ONE `v=spf1` TXT record (two = permerror = failed auth). Stay under SPF's 10-DNS-lookup limit. Example value:
   ```
   v=spf1 include:_spf.google.com ~all
   ```
3. **DKIM** — enable in the mailbox provider, publish the selector record. Example (Google Workspace, selector `google`):
   ```
   google._domainkey.<sending-domain>  TXT  "v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3..."
   ```
4. **DMARC** — start at `p=none` to monitor, move to `p=quarantine` after 2 clean weeks:
   ```
   _dmarc.<sending-domain>  TXT  "v=DMARC1; p=quarantine; rua=mailto:dmarc@<sending-domain>; pct=100"
   ```
5. **Verify all three resolve** before sending anything:
   ```powershell
   # PowerShell
   Resolve-DnsName -Type TXT <sending-domain> | Select-Object -Expand Strings          # expect one v=spf1 line
   Resolve-DnsName -Type TXT google._domainkey.<sending-domain> | Select-Object -Expand Strings
   Resolve-DnsName -Type TXT _dmarc.<sending-domain> | Select-Object -Expand Strings   # expect v=DMARC1
   ```
   ```sh
   # POSIX
   dig +short TXT <sending-domain>                      # expect one "v=spf1 ..." line
   dig +short TXT google._domainkey.<sending-domain>    # expect "v=DKIM1; ..."
   dig +short TXT _dmarc.<sending-domain>               # expect "v=DMARC1; ..."
   ```
   Empty output on any of the three = DO NOT SEND. Fix DNS first.
6. **Warmup schedule** (per mailbox; use the sequencer's built-in warmup pool):

   | Week | Sends/mailbox/day | Mix |
   |---|---|---|
   | 1-2 | 10-20 | warmup-pool traffic only, no cold sends |
   | 3 | 25-30 | begin cold sends at ≤10/day, rest warmup |
   | 4 | 35-45 | shift ratio toward cold |
   | 5+ | plateau **~50/mailbox/day** — hard ceiling | keep 10-20% warmup traffic running permanently |

7. **Scale with mailboxes, not volume-per-mailbox.** Need 500/day → ~10-12 mailboxes across 3-5 sending domains (2-3 mailboxes per domain), each individually warmed. One mailbox at 500/day is a self-report to the spam filter.
8. **Spam-complaint threshold: <0.1%** (roughly 1 complaint per 1,000 delivered — Gmail enforces this number via Postmaster Tools). At or above it: stop sending, audit list source and opt-out handling before resuming.
9. **Working unsubscribe path** (link or "reply STOP" honored within 24h) and `List-Unsubscribe` header enabled in the sequencer — Gmail/Yahoo require it for bulk senders.

## 4. Sequence Structure

- **3-5 touches over 2-3 weeks.** Example cadence: Day 1, Day 4, Day 9, Day 16 (optional Day 21 breakup). More than 5 touches raises complaints faster than replies.
- **Touch 1 — ≤90 words, plain text.** Must contain exactly: one sentence proving you looked at THEM specifically (trigger event, hire, tech in their stack, something they published) + one interest-question CTA ("worth a look?" — not "grab 30 minutes on my calendar"). **No links, no attachments, no images, no tracking pixel if the tool allows disabling it.** Links in touch 1 depress deliverability and replies simultaneously.
- **Follow-ups add a new angle each** (different proof point, different pain). Exactly one pure "bump" reply-in-thread is allowed per sequence; two is begging.
- **Touches 2-3 reply in the same thread** (keeps context, inherits any engagement signal).
- **Breakup email**: 2-3 sentences, closes the loop explicitly ("Assuming this isn't a priority — I'll stop here. If that changes, reply anytime."). Routinely the highest reply-rate touch; never skip it in a 5-touch sequence.
- **Vary copy across the batch** (spintax or per-segment variants). Hundreds of byte-identical bodies from fresh domains is a fingerprint Gmail clusters on.

## 5. Operating Gates

**GATE 1 — Count-and-preview before ANY delivery or send.**
Before delivering a list or launching a sequence, report: exact row count, the ICP filters used, and 5-10 sample rows. Then STOP and wait for explicit approval of that exact count.
- PASS: the human approved this count + these filters, this session.
- FAIL: any list delivered or any send started on a guess, a stale approval, or a different count than approved. Count ≠ pull ≠ deliver ≠ send — each is a separate authorization.

**GATE 2 — Verify-before-send.**
- PASS: 100% of the batch carries a verification status dated <30 days; 0 `invalid` rows present; catch-all policy (section 2) applied.
- FAIL: any row unverified, any verification undated, or verification scheduled "after the first batch goes out".

**GATE 3 — Suppression discipline.**
Maintain ONE suppression list containing: unsubscribes/opt-outs, all hard bounces (permanently), current customers, and open opportunities. Diff every batch against it before load:

```powershell
Compare-Object (Import-Csv batch.csv).email (Import-Csv suppression.csv).email -IncludeEqual -ExcludeDifferent
# any output = rows to remove before sending
```

```sh
# POSIX (no process substitution — works under dash/ash)
a=$(mktemp); b=$(mktemp)
cut -d, -f1 batch.csv | sort -u > "$a"
cut -d, -f1 suppression.csv | sort -u > "$b"
comm -12 "$a" "$b"
rm -f "$a" "$b"
# any output = rows to remove before sending
```

- PASS: zero overlap at send time.
- FAIL: emailing an unsubscriber (legal exposure: CAN-SPAM/GDPR/CASL) or cold-pitching a current customer.

**Reply-handling SLA.** Positive reply: human response within 4 business hours, same day at worst — a hot reply left overnight is a dead reply. All replies classified (positive / objection / referral / not-now / unsubscribe) within 24h. Any opt-out signal, however phrased ("not interested" counts), suppressed within 24h and always before that contact's next scheduled touch. Auto-replies (OOO) do not pause the SLA clock for the batch, but a bounce does — see section 6.

## 6. Metrics — Healthy Ranges and What to Do Below Them

| Metric | Healthy | Below/above range → diagnostic action |
|---|---|---|
| Open rate | >40% — but unreliable post-Apple-MPP/Gmail-prefetch; use as a trend line, never as a success metric | <40% and falling: suspect deliverability, not copy — run an inbox-placement/seed test (GlockApps-class), check Google Postmaster domain reputation, re-verify DNS (section 3.5) |
| Reply rate | >2-3% | <2%: copy or targeting problem — rewrite the touch-1 relevance sentence first (it fails most often), then tighten ICP filters; A/B one variable at a time |
| Positive-reply rate | >0.5-1% of delivered | below while total replies are healthy: offer/ICP mismatch, not copy — revisit who you're targeting and what you're offering before touching the email text |
| Bounce rate | <2% | ≥2% mid-batch: HALT all sends immediately, re-verify the entire remaining list, purge invalids, resume only after a clean re-verify |
| Spam-complaint rate | <0.1% | ≥0.1%: stop sending, audit list source and unsubscribe handling, reduce volume 50% on resume |

Bounce messages worth reading verbatim — map to action:

| Bounce text contains | Meaning | Action |
|---|---|---|
| `550 5.1.1` / `user unknown` / `does not exist` | hard bounce | suppress permanently; if these exceed 2% of the batch, halt and re-verify the rest |
| `550 5.7.1 ... blocked using Spamhaus` (or any DNSBL name) | sending IP/domain is blocklisted | stop ALL sending from that domain; check the named blocklist, file delisting, resume at warmup-week-3 volume |
| `421 4.7.0 ... unusual rate of unsolicited mail` | Gmail rate-limiting the sender | halve daily volume for 7 days, keep warmup traffic running |
| `452 4.2.2` / `mailbox full` | soft bounce | retry per sequencer default; suppress after 3 consecutive soft bounces |

## Done-Gate

An outbound task is done ONLY when: the deliverable matched the count approved in GATE 1, verification coverage was 100% and dated (GATE 2), suppression diff returned zero overlap (GATE 3), and — for sends — the batch's bounce and complaint rates came back under 2% / 0.1%. "Loaded into the sequencer" is not done; "sent and metrics within thresholds" is done.
