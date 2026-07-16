#!/usr/bin/env bash
# Open-source installer for T-ex LLM (host + web + optional backends).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "==> T-ex LLM installer"
echo "    root: $ROOT"

# --- Python host ---
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 required" >&2
  exit 1
fi

echo "==> Python $(python3 --version)"
python3 -m pip install -q -e ".[dev]" || python3 -m pip install -q -e .

# --- DB detect ---
echo "==> Detecting database…"
# shellcheck disable=SC1091
eval "$(bash "$ROOT/scripts/install/detect-db.sh")"
echo "    mode: ${DB_MODE} (${DB_DETAIL:-none})"

# --- .env ---
if [[ ! -f "$ROOT/.env" ]]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "==> Wrote .env from .env.example"
fi

# Append DB hints
if [[ "${DB_MODE}" == "postgres" && -n "${DATABASE_URL:-}" ]]; then
  if ! grep -q '^DATABASE_URL=' "$ROOT/.env" 2>/dev/null; then
    echo "DATABASE_URL=${DATABASE_URL}" >>"$ROOT/.env"
  fi
fi
if [[ "${DB_MODE}" == "supabase" ]]; then
  if [[ -n "${SUPABASE_URL:-}" ]] && ! grep -q '^SUPABASE_URL=' "$ROOT/.env" 2>/dev/null; then
    echo "SUPABASE_URL=${SUPABASE_URL}" >>"$ROOT/.env"
  fi
fi

# --- Optional NocoBase ---
PULL_NOCO="${TEX_PULL_NOCOBASE:-ask}"
if [[ "${PULL_NOCO}" == "ask" && -t 0 ]]; then
  read -r -p "Pull lightweight NocoBase backend via Docker? [y/N] " ans || ans=n
  case "${ans}" in
    y|Y|yes|YES) PULL_NOCO=yes ;;
    *) PULL_NOCO=no ;;
  esac
fi

if [[ "${PULL_NOCO}" == "yes" ]]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "WARN: docker not found; skip NocoBase" >&2
  else
    echo "==> Starting NocoBase (docker compose)…"
    docker compose -f "$ROOT/deploy/docker-compose.nocobase.yml" up -d
    echo "    NocoBase: http://127.0.0.1:13000"
  fi
fi

# --- Web console ---
if command -v npm >/dev/null 2>&1; then
  echo "==> Installing web console deps…"
  (cd "$ROOT/apps/web" && npm install)
else
  echo "WARN: npm not found; skip web install" >&2
fi

# --- Tailscale note ---
if command -v tailscale >/dev/null 2>&1; then
  echo "==> Tailscale detected: $(tailscale status --json 2>/dev/null | head -c 80 || echo ok)"
  echo "    Enable Tailscale SSH: https://tailscale.com/kb/1193/tailscale-ssh"
else
  echo "==> Tailscale not installed (optional for private SSH ops)"
fi

cat <<EOF

==> Install complete

Start host (API):
  cd $ROOT
  export LLM_PROVIDER=mock   # or openai + LLM_API_KEY
  python3 -m texllm.host.app

Start web console:
  cd $ROOT/apps/web
  npm run dev
  open http://127.0.0.1:5173

DB mode detected: ${DB_MODE}
Backup tips:
  Postgres:  pg_dump "\$DATABASE_URL" > backup.sql
  Supabase:  use dashboard backups or supabase db dump

EOF
