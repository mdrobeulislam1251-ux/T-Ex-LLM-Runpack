# T-ex LLM Quickstart

SaaS console + multi-agent host. Skill/design-system patterns inspired by Open Design; runtime is T-ex LLM.

## Requirements

- **Python** 3.9+
- **Node.js** 20+ (22 OK) for `apps/web`
- Optional: Docker (NocoBase / Postgres), Tailscale SSH

## One-shot installer

```bash
bash scripts/install/install.sh
```

Detects Postgres/Supabase, installs Python package, optional NocoBase, web deps.

## Dev (two terminals)

```bash
# Terminal A — host
cd /path/to/T-ex-LLM
export LLM_PROVIDER=mock
export HOST_API_KEY=change-me
python3 -m texllm.host.app

# Terminal B — web
cd apps/web
npm install
npm run dev
# → http://127.0.0.1:5173
```

Path-to-path routes: `/onboarding` → `/jobs` → `/jobs/:id` → `/brand` → `/settings`.

## Docker host

```bash
docker compose -f deploy/docker-compose.yml up -d --build
curl -s http://127.0.0.1:8080/health
```

Postgres profile:

```bash
docker compose -f deploy/docker-compose.yml --profile db up -d
```

## Open Design–style skills

| Skill | Path |
|-------|------|
| SaaS console | `skills/saas-console/SKILL.md` |
| Onboarding | `skills/saas-onboarding/SKILL.md` |
| Platform | `skills/agentic-platform/SKILL.md` |
| Design system | `design-systems/tex-neutral/DESIGN.md` |

Point Claude / Codex / Grok at the repo and load a skill for UI or agent work.

## Accessibility

- Skip link, focus management on onboarding steps
- `prefers-reduced-motion` disables 3D stage animation
- Status chips use text + color

## Database backup

```bash
# Postgres
pg_dump "$DATABASE_URL" > backup-$(date +%F).sql

# Supabase CLI (if linked)
supabase db dump -f backup.sql
```

## Tailscale SSH

```bash
# on server
tailscale up
# enable Tailscale SSH per https://tailscale.com/kb/1193/tailscale-ssh
ssh your-host.tailnet.ts.net
```

Save MagicDNS name in console **Settings**.
