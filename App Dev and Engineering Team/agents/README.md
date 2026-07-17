# agents/

Core agent execution engines and orchestration logic.

**Owns:** sub-agent definitions, reasoning loops, multi-agent orchestration,
and the execution runtime that dispatches work returned by Arion's router.

**Runtime:** the reusable engine lives in [`core/engine.py`](../../core/engine.py)
(`ExecutionEngine` — handler registry + `dispatch()` → `ExecutionResult`).
Register a sub-agent handler `(query, route) -> str` per workspace. Domain
handler modules for this folder are loaded by path (the folder name contains
spaces, so it is not a normal Python import target). Status: **Phase 3 done.**

**TDD contract:** every engine or orchestrator added here must land with a
failing test in `tests/` *before* its structural logic (see `tasks.md`).
