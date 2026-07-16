# SKILL.md: Arion App Dev & Engineering

## Description
This skill governs code generation, Test-Driven Development loops, and system
deployment for the engineering track. Arion reads this file to learn what it
is permitted to do when a request routes to an engineering workspace.

## Intent Hooks
- Keywords: `[agent, sub-agent, execution engine, orchestrator]` -> Route to: `.\agents\`
- Keywords: `[hook, runtime, trigger, event, middleware]` -> Route to: `.\runtime_hooks\`
- Keywords: `[deploy, ssh, tailnet, tl-host, playwright, release]` -> Route to: `.\deployments\`

## Execution Rules
1. Never generate placeholders like `// TODO` or `// implement here`.
   Deliver complete, runnable logic blocks.
2. TDD is mandatory: write a failing test first (RED), implement to pass
   (GREEN), then refactor. No feature logic lands without a preceding
   failing-test commit.
3. Deployments run over the Tailnet IP mesh via SSH to `tl-host`. A failing
   dry-run/health-check test must exist before any real deploy step.
4. Post-deploy verification uses headless Playwright to assert the target is
   up; a down target must fail the smoke test.
5. Keep changes synced to the `Robeul-Dev-Update` branch.

<!--
Path portability note: hooks use Windows-style `.\folder\` notation for the
operator workstation, but Arion resolves them relative to THIS skill file's
directory so the routes hold on Linux and the tl-host server. The
machine-readable route map is `config/routing.json`.
-->
