---
description: Onboard a new company — you give the name and vision, the research team generates the full brain; only credentials and brand assets are asked
---

Run the `company-onboarding` skill now. $ARGUMENTS may contain the company name.

Check `companies/<slug>/brain-request.json` first (dashboard Brain Studio requests) —
if present, use its briefing and do not re-ask. Otherwise ask only two things: the
company name and a free-text "tell me about your company — structure and vision".
The research team (research-lead, market-analyst, product-strategist,
content-strategist, cto) generates scope, vision, mission, emotion/tone, audience,
voice, and stack. One confirm pass with the user, then ask ONLY for brand assets and
credentials (stored in gitignored `.env`, profile keeps env var names only). Finish
with data-engineer deriving the schema and cto reviewing it per `data-schema-design`.
