# gmail/

Skill home for the **Gmail** intent hook (`gmail, email, send mail, inbox`).

Holds the Gmail connector logic: read/search inbox, draft, send, and label.
Related low-level adapter code lives in `../tool_handlers/`.

**TDD contract:** each Gmail action ships with a failing test (mocking the
Gmail API boundary) before the integration call is written. See `tasks.md`.
