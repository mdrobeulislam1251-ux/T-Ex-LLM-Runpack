# support/

Skill home for the **support** intent hook (`support, ticket, client, help`).

Holds support/escalation workflow logic. Related pipeline automation lives in
`../pipelines/`.

**TDD contract:** each support state transition ships with a failing test
(new → triaged → escalated) before the stage logic is written. See `tasks.md`.
