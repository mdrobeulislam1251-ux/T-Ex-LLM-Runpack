#!/usr/bin/env bash
# T-Ex LLM launcher — portable standalone mode (macOS / Linux).
# Resolves everything relative to this file's location; never hardcode a path here.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEX_HOME="$HERE/.claude-tex"
if [ ! -f "$TEX_HOME/CLAUDE.md" ]; then
  echo "[T-Ex] ERROR: .claude-tex home not found next to launcher ($TEX_HOME)" >&2
  exit 1
fi

# Skills live ONCE in the runpack (plugins/tex-llm/skills — single source of truth).
# Mirror them into the standalone home on every launch so both modes never drift.
SKILLS_SRC="$HERE/../plugins/tex-llm/skills"
SKILLS_DST="$TEX_HOME/skills"
if [ -d "$SKILLS_SRC" ]; then
  if command -v rsync >/dev/null 2>&1; then
    mkdir -p "$SKILLS_DST"
    rsync -a --delete "$SKILLS_SRC/" "$SKILLS_DST/"
  else
    rm -rf "$SKILLS_DST"
    cp -R "$SKILLS_SRC" "$SKILLS_DST"
  fi
  echo "[T-Ex] Skills synced from runpack: $SKILLS_SRC"
elif [ ! -d "$SKILLS_DST" ]; then
  echo "[T-Ex] ERROR: runpack skills not found at $SKILLS_SRC and no local skills/ present" >&2
  exit 1
fi

export CLAUDE_CONFIG_DIR="$TEX_HOME"
echo "[T-Ex] Config home: $TEX_HOME"

# Launch in the directory the user invoked from (their project), passing through any args.
exec claude "$@"
