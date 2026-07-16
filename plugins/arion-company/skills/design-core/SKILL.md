---
name: design-core
description: The design team's core method — research, strategy, flows, visuals, tokens, and handoff — all driven by the company brain's emotion/tone. Use for any design effort from a single screen to a full product design.
---

# Design Core — From Company Brain to Shipped Interface

Design at Arion is not decoration: it is the company brain's emotion and vision made
visible. Every design decision must trace back to a brain field or a research finding.

## Step 0 — Load the brain, set direction (design-director)

From the brain's `emotion_tone`, `vision`, and `target_audience`, the design-director
writes a one-page direction: personality (3 adjectives), density (airy ↔ dense),
color temperament, type character, motion character (snappy ↔ soft). All later work is
reviewed against this page.

## Step 1 — Research (ux-researcher)

- Heuristic audit of the current product (if any) — Nielsen's 10, listed violations.
- Competitor UX teardown: 3–5 products the target audience already uses; extract
  patterns users will expect.
- Output: ranked findings with evidence. No design starts on pure assumption.

## Step 2 — Strategy & structure (ux-designer)

- User flows per feature: entry → decisions → success/failure exits.
- Information architecture: navigation model that survives the roadmap.
- Low-fidelity wireframes; structure locks BEFORE visuals begin.
- Every screen lists its edge states: empty, loading, error, denied, offline.

## Step 3 — Visual design (ui-designer + brand-designer)

- Brand-designer supplies the palette, type stack, and usage rules from
  `companies/<slug>/brand/brand.md`. Nobody improvises colors.
- High-fidelity specs with exact values: grid, spacing scale (4/8px), type scale,
  color tokens, radii, shadows.
- Every component specced in all states: default, hover, focus, active, disabled,
  loading, error.
- Contrast: WCAG AA minimum on every text/background pair — checked, not assumed.

## Step 4 — Motion (motion-designer)

- Motion language: standard durations (e.g. 120/200/300ms), easing curves, what
  animates and what never does.
- `prefers-reduced-motion` behavior specified for every animation.

## Step 5 — Review gate (design-director)

APPROVED / REVISE with numbered notes. Nothing reaches engineering unreviewed.
Review checks: direction fidelity, brand compliance, state completeness,
accessibility, feasibility.

## Step 6 — Tokens & handoff (design-system-engineer)

- Semantic token files generated for the project's stack (CSS variables / Tailwind
  config / native themes).
- Handoff package to frontend-engineer: specs, tokens, assets, state matrix,
  motion table.
- After implementation, design-system-engineer reviews the built UI against the spec
  state-for-state before merge. Drift is a defect.

## Working rules

- Feedback is specific and referenced ("increase contrast on secondary buttons to
  4.5:1"), never vibes ("make it pop").
- Design debt is logged like tech debt — in the backlog with severity.
- Marketing assets follow the same brand file; brand-designer audits before publish.
