# tool_handlers/

External tool handlers and connector integrations.

**Owns:** Gmail, Asana, calendar, Slack, Notion, Linear, and Drive handlers —
the adapters that let Arion act on external services.

**TDD contract:** each handler must ship with a failing test (mocking the
external API boundary) before the integration call is written (see `tasks.md`).
