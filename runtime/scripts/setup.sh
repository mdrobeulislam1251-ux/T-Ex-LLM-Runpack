#!/usr/bin/env bash
# T-ex LLM — single setup for macOS / Linux / Ubuntu / Windows (Git Bash or WSL)
# Usage:
#   bash scripts/setup.sh
#   bash scripts/setup.sh --port 3006 --non-interactive
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PORT="${TEX_PORT:-3006}"
NON_INTERACTIVE=0
SKIP_WEB_BUILD=0
API_KEY="${HOST_API_KEY:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    --non-interactive|--yes|-y) NON_INTERACTIVE=1; shift ;;
    --skip-web-build) SKIP_WEB_BUILD=1; shift ;;
    --api-key) API_KEY="$2"; shift 2 ;;
    -h|--help)
      cat <<EOF
T-ex LLM setup

Options:
  --port N              Public port for API + web UI (default: 3006)
  --api-key KEY         Host API key (default: generate or change-me)
  --non-interactive     No prompts
  --skip-web-build      Skip npm run build
EOF
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

os_name="$(uname -s 2>/dev/null || echo unknown)"
echo "==> T-ex LLM setup"
echo "    root: $ROOT"
echo "    os:   $os_name"

# --- prerequisites ---
need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $1" >&2
    exit 1
  fi
}

PY="$(command -v python3 || command -v python || true)"
if [[ -z "$PY" ]]; then
  echo "ERROR: required command not found: python3 (or python)" >&2
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "WARN: npm not found — web UI build will be skipped. Install Node.js 20+."
  SKIP_WEB_BUILD=1
fi

# --- interactive port / key ---
if [[ "$NON_INTERACTIVE" -eq 0 && -t 0 ]]; then
  read -r -p "HTTP port for web UI + API [${PORT}]: " in_port || true
  if [[ -n "${in_port:-}" ]]; then
    PORT="$in_port"
  fi
  if [[ -z "$API_KEY" ]]; then
    read -r -p "API key [change-me]: " in_key || true
    API_KEY="${in_key:-change-me}"
  fi
else
  API_KEY="${API_KEY:-change-me}"
fi

# validate port
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [[ "$PORT" -lt 1 || "$PORT" -gt 65535 ]]; then
  echo "ERROR: invalid port: $PORT" >&2
  exit 1
fi

echo "==> Port: $PORT"
echo "==> Python: $("$PY" --version)"

# --- virtualenv (PEP 668-safe: never install into the system interpreter) ---
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo "==> Creating virtualenv .venv…"
  "$PY" -m venv "$ROOT/.venv"
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate" 2>/dev/null || source "$ROOT/.venv/Scripts/activate"
  PY="$(command -v python)"
fi

# --- python package ---
echo "==> Installing Python package…"
"$PY" -m pip install -q -e ".[dev]" 2>/dev/null || "$PY" -m pip install -q -e .

# --- web ---
if [[ "$SKIP_WEB_BUILD" -eq 0 ]]; then
  echo "==> Building web UI…"
  (cd "$ROOT/apps/web" && npm install && npm run build)
else
  echo "==> Skipping web build"
fi

# --- .env ---
if [[ ! -f "$ROOT/.env" ]]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
fi

# upsert env keys (portable-ish)
upsert_env() {
  local key="$1" val="$2" file="$ROOT/.env"
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    # shellcheck disable=SC2001
    if sed --version >/dev/null 2>&1; then
      sed -i "s|^${key}=.*|${key}=${val}|" "$file"
    else
      sed -i '' "s|^${key}=.*|${key}=${val}|" "$file"
    fi
  else
    echo "${key}=${val}" >>"$file"
  fi
}

upsert_env "HOST_PORT" "$PORT"
upsert_env "HOST_BIND" "0.0.0.0"
upsert_env "HOST_API_KEY" "$API_KEY"
upsert_env "SERVE_WEB" "true"
upsert_env "ALLOW_LOCAL_CLI" "true"
upsert_env "LLM_PROVIDER" "${LLM_PROVIDER:-auto}"

# --- DB detect (informational) ---
if [[ -x "$ROOT/scripts/install/detect-db.sh" ]]; then
  echo "==> Database probe…"
  bash "$ROOT/scripts/install/detect-db.sh" || true
fi

# --- agent detect ---
echo "==> Scanning for terminal AI CLIs…"
"$PY" -m texllm.cli agents || true

cat <<EOF

========================================================================
  Setup complete
========================================================================

Start (API + Web UI on one port):

  cd $ROOT
  source .venv/bin/activate      # Git Bash on Windows: source .venv/Scripts/activate
  set -a; source .env; set +a    # bash/zsh
  python -m texllm.cli serve

  # or:
  texllm serve --port $PORT

Open the console:
  http://127.0.0.1:${PORT}/

Health:
  curl -s http://127.0.0.1:${PORT}/health

Detect local agents (no API key):
  python3 -m texllm.cli agents

Docs:
  docs/QUICKSTART.md          multi-OS install
  docs/REMOTE-ACCESS.md       Tailscale / LAN / DNS

Default port is ${PORT}. Change anytime with --port or HOST_PORT in .env
========================================================================
EOF
