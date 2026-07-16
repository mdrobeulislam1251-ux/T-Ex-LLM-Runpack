#!/usr/bin/env bash
# Auto-detect Postgres or Supabase for T-ex LLM installer.
set -euo pipefail

MODE="none"
DETAIL=""

if [[ -n "${DATABASE_URL:-}" ]]; then
  if [[ "${DATABASE_URL}" == *"supabase"* ]] || [[ -n "${SUPABASE_URL:-}" ]]; then
    MODE="supabase"
    DETAIL="DATABASE_URL / SUPABASE_URL env present"
  else
    MODE="postgres"
    DETAIL="DATABASE_URL env present"
  fi
elif [[ -n "${SUPABASE_URL:-}" ]]; then
  MODE="supabase"
  DETAIL="SUPABASE_URL=${SUPABASE_URL}"
elif command -v psql >/dev/null 2>&1; then
  if psql -d postgres -c "SELECT 1" >/dev/null 2>&1; then
    MODE="postgres"
    DETAIL="local psql can connect to postgres"
  elif pg_isready >/dev/null 2>&1; then
    MODE="postgres"
    DETAIL="pg_isready reports accepting connections"
  fi
elif [[ -S /tmp/.s.PGSQL.5432 ]] || [[ -S /var/run/postgresql/.s.PGSQL.5432 ]]; then
  MODE="postgres"
  DETAIL="Postgres unix socket found"
fi

# Docker postgres / supabase containers
if [[ "${MODE}" == "none" ]] && command -v docker >/dev/null 2>&1; then
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -Eiq 'postgres|supabase'; then
    MODE="postgres"
    DETAIL="docker container named postgres/supabase running"
  fi
fi

echo "DB_MODE=${MODE}"
echo "DB_DETAIL=${DETAIL}"
