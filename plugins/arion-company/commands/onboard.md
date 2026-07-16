---
description: Onboard a new company/app into the Arion runpack — collects name, brand assets, DB & n8n credentials, and builds the company brain
---

Run the `company-onboarding` skill now. Ask the user every onboarding question group
(identity; scope/vision/emotion; brand assets; DB credentials; n8n credentials; other
config), store secrets only in `.env` (ensure it is gitignored first), write the company
brain to `companies/<slug>/profile.json`, set it active, then have data-engineer derive
the initial schema and submit it to cto for review per the `data-schema-design` skill.

$ARGUMENTS may contain the company name to pre-fill question 1.
