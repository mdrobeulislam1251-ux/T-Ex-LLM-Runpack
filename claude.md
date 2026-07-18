# Arion Core Engine Rules## 1. Zero-Laziness Enforcement- You are strictly forbidden from writing partial code or templates.- You must write fully realized, compilation-ready code blocks.
- If editing a file, you must rewrite or safely block-replace the target sections completely. Never truncate with code comments like `// rest of code here`.
## 2. Test-Driven Development (TDD) Gate- No production feature code may be written unless an associated failing test case exists in the workspace first.- Every milestone task must execute a localized shell test command before it is declared complete.
## 3. Remote Verification Architecture- Server-side interactions must be routed securely via SSH over the Tailnet profile (`tl-host`).- Use headless Playwright automation checkpoints to visually verify frontends or external API state loops.

## 4. n8n Workflow Building
- This project ships the official n8n skills under `.claude/skills/`. When working with n8n workflows, nodes, expressions, or the n8n MCP tools, ALWAYS start by loading the `using-n8n-skills-official` meta-skill and follow its routing into the matching capability skill before acting.
- Requires an n8n instance with the instance-level MCP server enabled (see `.claude/skills/README.md`).
