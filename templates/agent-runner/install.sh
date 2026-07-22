#!/usr/bin/env bash
# install.sh — install the tex-agent-runner as a systemd service on the n8n host (aidata).
# Idempotent. Run as root. Reads the existing n8n gateway token so the runner reports
# back to Linear through the same proxy (no Linear key on this service).
set -euo pipefail

N8N_ENV="${N8N_ENV:-/data/apps/n8n/.env}"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR=/opt/tex-agent-runner
ENV_FILE=/etc/tex-agent-runner.env

command -v node >/dev/null || { echo "node not found — install Node 20+ first"; exit 1; }
command -v claude >/dev/null || echo "WARN: claude CLI not on PATH yet (npm i -g @anthropic-ai/claude-code)"

id texagent >/dev/null 2>&1 || useradd -m -s /bin/bash texagent
install -d -o texagent -g texagent "$APP_DIR"
install -o root -g root -m 0644 "$SRC_DIR/runner.mjs" "$APP_DIR/runner.mjs"

if [ ! -f "$ENV_FILE" ]; then
  GW="$(grep -E '^TEX_GATEWAY_TOKEN=' "$N8N_ENV" 2>/dev/null | cut -d= -f2- || true)"
  [ -n "$GW" ] || { echo "Could not read TEX_GATEWAY_TOKEN from $N8N_ENV — set N8N_ENV or create $ENV_FILE by hand"; exit 1; }
  RT="$(openssl rand -hex 24)"
  sed -e "s|__generated_by_installer__|$RT|" -e "s|__copied_from_n8n__|$GW|" \
      "$SRC_DIR/tex-agent-runner.env.example" > "$ENV_FILE"
  chmod 600 "$ENV_FILE"; chown root:root "$ENV_FILE"
  echo "wrote $ENV_FILE (RUNNER_TOKEN generated, gateway token copied)"
else
  echo "$ENV_FILE exists — left as-is"
fi

install -o root -g root -m 0644 "$SRC_DIR/tex-agent-runner.service" /etc/systemd/system/tex-agent-runner.service
systemctl daemon-reload
systemctl enable --now tex-agent-runner
sleep 2
systemctl --no-pager --full status tex-agent-runner | head -6 || true
echo "--- health:"
curl -s http://127.0.0.1:"$(grep -E '^RUNNER_PORT=' "$ENV_FILE" | cut -d= -f2)"/health || echo "(not answering yet)"
echo
echo "Next: set CLAUDE_CODE_OAUTH_TOKEN in $ENV_FILE (sudo -u texagent claude setup-token), then: systemctl restart tex-agent-runner"
