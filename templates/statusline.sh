#!/usr/bin/env bash
# T-Ex LLM status line — portable template.
# Renders: ◆ <model> · <workspace> · ⎇ <branch>* · <N> changed · $<cost>
# Reads Claude Code's status JSON on stdin. No jq/node dependency (grep/sed only).
#
# Install: copy to ~/.claude/statusline.sh, then in ~/.claude/settings.json add:
#   "statusLine": { "type": "command", "command": "bash \"$HOME/.claude/statusline.sh\"" }
# On Windows with Git Bash, use the absolute POSIX path, e.g.
#   "command": "bash \"/c/Users/<you>/.claude/statusline.sh\""
input=$(cat)

field() { printf '%s' "$input" | grep -oE "\"$1\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" | head -1 | sed -E 's/.*:[[:space:]]*"([^"]*)"/\1/'; }
num()   { printf '%s' "$input" | grep -oE "\"$1\"[[:space:]]*:[[:space:]]*[0-9.]+" | head -1 | sed -E 's/.*:[[:space:]]*//'; }

model=$(field display_name)
dir=$(field current_dir); [ -z "$dir" ] && dir=$(field cwd)
cost=$(num total_cost_usd)

ws=$(basename "$dir" 2>/dev/null)
branch=""; dirty=""; changed=""
if [ -n "$dir" ] && cd "$dir" 2>/dev/null && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
  st=$(git status --porcelain 2>/dev/null)
  [ -n "$st" ] && dirty="*"
  changed=$(printf '%s\n' "$st" | grep -c . 2>/dev/null)
fi

out="◆ ${model:-model?}"
[ -n "$ws" ] && out="$out · $ws"
[ -n "$branch" ] && out="$out · ⎇ ${branch}${dirty}"
[ -n "$changed" ] && [ "$changed" != "0" ] && out="$out · ${changed} changed"
if [ -n "$cost" ]; then
  fmt=$(printf '%.2f' "$cost" 2>/dev/null) || fmt="$cost"
  out="$out · \$$fmt"
fi
printf '%s' "$out"
