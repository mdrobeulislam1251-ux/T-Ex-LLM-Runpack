# runtime_hooks/

Runtime hooks, lifecycle interceptors, and event middleware.

**Owns:** pre/post execution hooks, lifecycle event handlers, and the
keyword-trigger interception layer that feeds Arion's router.

**TDD contract:** each hook must be pinned by a failing test asserting its
fire condition before the hook body is written (see `tasks.md`).
