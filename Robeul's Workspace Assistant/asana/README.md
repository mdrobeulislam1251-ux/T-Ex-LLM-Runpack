# asana/

Skill home for the **Asana** intent hook (`asana, project, board, ticket`).

Holds Asana connector logic: create/update tasks, projects, and status.
Related low-level adapter code lives in `../tool_handlers/`.

**TDD contract:** each Asana action ships with a failing test asserting the
request payload shape before the integration call is written. See `tasks.md`.
