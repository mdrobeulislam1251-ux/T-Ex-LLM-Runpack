# runtime_hooks/

Runtime hooks, lifecycle interceptors, and event middleware.

**Owns:** pre/post execution hooks, lifecycle event handlers, and the
keyword-trigger interception layer that feeds Arion's router.

**Runtime:** the reusable layer lives in [`core/hooks.py`](../../core/hooks.py)
(`QueryHook` wires router → engine; `LifecycleChain` runs ordered pre/post
hooks over a shared context dict — pre-hooks may rewrite the query before it
is routed). Drive it end-to-end with `python3 arion.py exec "<query>"`.
Status: **Phase 2 done.**

**TDD contract:** each hook must be pinned by a failing test asserting its
fire condition before the hook body is written (see `tasks.md`).
