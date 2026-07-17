# SKILL.md: Arion Workspace Orchestrator

## Description
This skill handles global task routing, automation hooks, and developer
handoffs for Robeul's active workspace. Arion reads this file to learn which
sub-agent folder owns an incoming request before taking any action.

## Intent Hooks
- Keywords: `[gmail, email, send mail, inbox]` -> Route to: `.\gmail\`
- Keywords: `[asana, project, board, ticket]` -> Route to: `.\asana\`
- Keywords: `[task, todo, list, scheduling]` -> Route to: `.\tasks\`
- Keywords: `[support, ticket, client, help]` -> Route to: `.\support\`

## Execution Rules
1. Never generate placeholders like `// TODO`. Implement full logic blocks.
2. Maintain sync with the `Robeul-Dev-Update` branch continuously.
3. If an external action is requested, parse the target folder environment
   variables before running shell tasks.
4. Honor the TDD gate: a failing test in `core_router_test.py` (or `tests/`)
   must exist before any skill logic is written.

<!--
Path portability note: hooks are written with Windows-style `.\folder\`
notation to match the operator workstation, but Arion resolves them relative
to THIS skill file's directory, so the same routes work on Linux and the
tl-host server. The machine-readable equivalent of this table lives in
`config/routing.json` (schema arion.routing/v1); keep the two in sync.
-->
