# pipelines/

Support pipelines, notification fan-out, and workflow automation.

**Owns:** support/escalation workflows, notification routing, and
multi-step automations that chain tool handlers together.

**TDD contract:** each pipeline stage must have a failing test asserting its
transition before the stage logic is implemented (see `tasks.md`).
