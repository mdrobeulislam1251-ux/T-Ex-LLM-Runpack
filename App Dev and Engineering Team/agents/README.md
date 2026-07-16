# agents/

Core agent execution engines and orchestration logic.

**Owns:** sub-agent definitions, reasoning loops, multi-agent orchestration,
and the execution runtime that dispatches work returned by Arion's router.

**TDD contract:** every engine or orchestrator added here must land with a
failing test in `tests/` *before* its structural logic (see `tasks.md`).
