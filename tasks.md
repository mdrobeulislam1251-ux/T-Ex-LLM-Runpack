# Arion — Automated Execution Roadmap (TDD Blueprint)

> **Enforcement rule — non-negotiable.** Every feature below is implemented
> in strict Test-Driven Development order:
>
> 1. **RED** — draft a *failing* test that pins the intended behaviour.
> 2. **GREEN** — write the minimum structural logic to make it pass.
> 3. **REFACTOR** — clean up with the test still green.
>
> A pull request that adds feature logic **without a preceding failing test
> commit** violates this blueprint and must be rejected. No structural logic
> is written before its test exists and fails.

## Legend

- `[x]` done · `[~]` in progress · `[ ]` not started
- Each task lists its **RED test** first, then the **GREEN implementation**.

---

## Phase 0 — Workspace bootstrap ✅

- [x] **RED** `tests/test_router.py::SchemaIntegrityTests::test_workspace_folders_exist_on_disk`
- [x] **GREEN** Create the two-track file tree
      (`App Dev and Engineering Team/`, `Robeul's Workspace Assistant/`)
- [x] **GREEN** Author `config/routing.json` (keyword → workspace map)
- [x] **GREEN** Author `ARCHITECTURE.md` (initialization schema / file tree)

## Phase 1 — Keyword-triggered routing engine ✅

- [x] **RED** Config loads & validates (`RoutingConfigTests`)
- [x] **RED** Engineering-track routing (`EngineeringTrackRoutingTests`)
- [x] **RED** Workspace-track routing (`WorkspaceTrackRoutingTests`)
- [x] **RED** Scoring, word-boundary, and fallback (`ScoringAndFallbackTests`)
- [x] **GREEN** `core/router.py` — `Router`, `Route`, `RouteMatch`
- [x] **GREEN** `arion.py` CLI — `route`, `list`, `schema`
- [x] **VERIFY** `python3 -m unittest discover -s tests -v` → 17 passing

## Phase 2 — Runtime hooks & interception ✅

> Workspace: `App Dev and Engineering Team/runtime_hooks/` ·
> Engine: `core/hooks.py`

- [x] **RED** `tests/test_hooks.py::QueryHookTests` — assert an incoming
      query is routed then dispatched, and unmatched queries hit the default.
- [x] **GREEN** `core/hooks.py::QueryHook` — routes (post pre-hooks) and
      dispatches to the resolved workspace.
- [x] **RED** `tests/test_hooks.py::LifecycleOrderTests` — assert pre runs
      before body, post after; pre may rewrite the query before routing.
- [x] **GREEN** `core/hooks.py::LifecycleChain` — ordered pre/post chain
      over a shared context dict.

## Phase 3 — Agent execution engine ✅

> Workspace: `App Dev and Engineering Team/agents/` · Engine: `core/engine.py`

- [x] **RED** `tests/test_engine.py::EngineTests` — routed task is handed to
      the correct handler; result carries route metadata.
- [x] **GREEN** `core/engine.py::ExecutionEngine` — handler registry +
      `dispatch()` returning `ExecutionResult`.
- [x] **RED** unknown-workspace + duplicate-registration guards.
- [x] **GREEN** `UnknownWorkspaceError` + duplicate-registration `ValueError`.
- [x] **GREEN** `build_acknowledger_engine()` + `arion.py exec` drive the full
      query → hook → router → engine → handler pipeline end-to-end.
- [x] **VERIFY** `python3 -m unittest discover -s tests` → 27 passing.

## Phase 4 — External tool handlers `[ ]`

> Workspace: `Robeul's Workspace Assistant/tool_handlers/`

- [ ] **RED** `test_gmail_handler.py` — mock the Gmail boundary; assert a
      "read inbox" intent calls the handler exactly once.
- [ ] **GREEN** Implement `tool_handlers/gmail.py`.
- [ ] **RED** `test_asana_handler.py` — mock Asana; assert task creation
      payload shape.
- [ ] **GREEN** Implement `tool_handlers/asana.py`.

## Phase 5 — Support pipelines `[ ]`

> Workspace: `Robeul's Workspace Assistant/pipelines/`

- [ ] **RED** `test_pipelines.py::test_escalation_transitions` — assert a
      support ticket advances new → triaged → escalated.
- [ ] **GREEN** Implement `pipelines/support.py` state machine.

## Phase 6 — Deployment pipeline `[ ]`

> Workspace: `App Dev and Engineering Team/deployments/`

- [ ] **RED** `test_deploy.py::test_dry_run_healthcheck` — assert a dry-run
      deploy returns a health-check verdict without touching `tl-host`.
- [ ] **GREEN** Implement `deployments/deploy.py` (Tailnet SSH → `tl-host`).
- [ ] **RED** `test_deploy.py::test_playwright_smoke_asserts_up` — assert the
      Playwright post-deploy smoke test fails when the target is down.
- [ ] **GREEN** Wire Playwright post-deploy verification.

---

## Running the suite

```bash
# Preferred
python3 -m pytest tests/ -q

# Zero-dependency fallback (no pytest required)
python3 -m unittest discover -s tests -v
```

## Definition of Done (per feature)

1. A failing test existed and was committed **before** the implementation.
2. The implementation makes that test pass.
3. The full suite is green.
4. The change is committed to `claude/arion-workspace-setup-esnpc9` and,
   when promoted, synced to `Robeul-Dev-Update`.
