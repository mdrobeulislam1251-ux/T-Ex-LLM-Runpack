# T-Ex standalone launcher (portable mode)

The second distribution mode of the runpack: **one T-Ex agent** (senior full-stack
engineer + systems operator + product strategist in a single persona) instead of the
53-agent company. Use it when you want the execution-first solo agent on any machine
without installing the Claude Code plugin.

## Launch

```powershell
# From any project directory:
& "<path-to-repo>\launcher\launch-tex.ps1"
```

The launcher sets `CLAUDE_CONFIG_DIR` to the `.claude-tex` home next to it, mirrors
the skill set from `plugins/tex-llm/skills/` (the single source of truth — synced on
every launch so the two modes never drift), then starts Claude Code in your current
directory.

## What's inside

- `.claude-tex/CLAUDE.md` — the T-Ex persona and behavior contract (probe never
  assume, exact task only, done = run-verified, single path, portable output).
- `.claude-tex/skills/` — synced from the runpack at launch; not tracked in git.

## Company brains

Standalone mode follows the same brain rule as the plugin: brains live in
`<project-root>/.tex-llm/companies/` of the project you launch in — never inside
this repo. See rule 0 in the repo root `CLAUDE.md`.
