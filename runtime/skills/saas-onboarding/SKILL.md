---
name: saas-onboarding
description: 3D/motion onboarding for T-ex LLM SaaS with skip, a11y, and clean redirect into the console. Use for onboarding, first-run, welcome flow, or /saas-onboarding.
od:
  mode: prototype
  design_system:
    requires: tex-neutral
---

# SaaS onboarding skill

## Steps (path-to-path)
1. `/onboarding` welcome — product value
2. `/onboarding/agents` — team runner story
3. `/onboarding/brand` — optional brand tweak
4. `/onboarding/connect` — host URL + API key smoke test
5. Redirect → `/jobs` (durable: set `texllm.onboarded=1`)

## Motion
- CSS 3D card stage; disable if `prefers-reduced-motion: reduce`
- Always show **Skip** and **Continue**
- Focus first heading on step change

## Acceptance
- Completing or skipping never blocks console use
- Revisit from Settings → “Replay onboarding”
