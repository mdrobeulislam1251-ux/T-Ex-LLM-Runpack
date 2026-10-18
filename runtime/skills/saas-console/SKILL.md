---
name: saas-console
description: Build or extend the T-ex LLM SaaS web console — agentic jobs UI, path-based navigation, brand menu, a11y, onboarding. Use when user says SaaS UI, control plane, console, dashboard, or /saas-console.
od:
  mode: prototype
  design_system:
    requires: tex-neutral
triggers:
  - saas ui
  - agent console
  - control plane
  - web dashboard
---

# SaaS console skill

## Goal
Ship operator UX for T-ex LLM that feels product-grade: durable routes, agentic job flow, brand customization, accessible motion.

## Stack
- `apps/web` — Vite + React + TypeScript
- Host API — `texllm` on `HOST_PORT` (default 8080)
- Design system — `design-systems/tex-neutral/DESIGN.md`

## Workflow
1. Read DESIGN.md tokens; never invent a second palette without Brand menu.
2. Keep routes path-to-path (`/`, `/onboarding`, `/jobs`, `/jobs/:id`, `/settings`, `/brand`).
3. Jobs: create → poll → show handoffs / review_passed.
4. Respect `prefers-reduced-motion`.
5. Persist brand tokens and last project in `localStorage`.
6. Settings expose: Host URL, API key, DB mode (none/postgres/supabase), Tailscale notes, optional NocoBase URL.

## Output contract
- Working UI with keyboard access
- No dead ends: every path has Back / Home
- Loading and error states for host calls
- Document env in `.env.example` / `apps/web/.env.example`
