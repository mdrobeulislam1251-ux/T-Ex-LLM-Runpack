# tasks/inbox/

**Default fallback workspace.**

Any task query that matches no keyword trigger in
[`config/routing.json`](../../../config/routing.json) lands here for manual
triage. If items pile up with a recognizable theme, add a keyword to the
appropriate route (and a test in `tests/test_router.py`) so they route
automatically next time.
