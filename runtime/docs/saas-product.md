# T-ex LLM — SaaS console product

Hyper-agentic control plane inspired by [Open Design](https://github.com/nexu-io)-style **skills + design systems**, wired to the T-ex host and team runners.

## Product goals

| Pillar | Delivery |
|--------|----------|
| **Agentic ops** | Job console: submit goals, stream status, review handoffs |
| **SaaS UX** | Path-to-path navigation, durable sessions, clean redirects |
| **Onboarding** | Motion + lightweight 3D stage, accessible by default |
| **Brand** | Live customization menu (tokens → CSS variables) |
| **Data** | Auto-detect Postgres / Supabase; optional NocoBase backend |
| **Access** | Optional Tailscale SSH for private operator access |
| **Durability** | LocalStorage brand + project state; DB for jobs when configured |

## Architecture (local product)

```
Browser (apps/web)
    │  /api proxy or VITE_HOST_URL
    ▼
texllm Host API  (:8080)     ← team runners + firmware
    │
    ├─ mock | OpenAI-compat LLM
    │
    └─ optional: Postgres / Supabase (job history, tenants)
         optional: NocoBase (low-code admin)
         optional: Tailscale SSH (ops plane)
```

## Execution modes (Open Design mapping)

| Mode | T-ex equivalent |
|------|-----------------|
| Local CLI | Grok / Claude / Codex on repo playbooks |
| API / daemon | Host `POST /v1/jobs` + poll |
| Skills | `skills/*` + `design-systems/*` for UI generation |
| Design system | CSS tokens + Brand menu |

## Installer contract

`scripts/install/install.sh`:

1. Detect OS and Python.
2. Auto-detect **Postgres** (local socket / `DATABASE_URL`) or **Supabase** (env / project URL).
3. Offer optional **NocoBase** pull (Docker) for lightweight admin backend.
4. Write `.env` and print Tailscale SSH notes if enabled.
5. Start host + web.

## Accessibility

- Prefer `prefers-reduced-motion` (disable 3D/parallax).
- Keyboard paths for all primary actions.
- Focus rings, ARIA landmarks, contrast-safe brand tokens.
- Skip link to main content.

## Brand menu

Persists to `localStorage` key `texllm.brand.v1`:

- primary / accent / surface / radius / density / logo text
- applies as `--tex-*` CSS variables on `:root`
