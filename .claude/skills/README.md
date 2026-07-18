# n8n Workflow Builder Skills (vendored)

The official n8n skills suite — 14 Claude Code skills for building and editing
n8n workflows through n8n's instance-level MCP server. Each skill is a
`SKILL.md` (with `name` + `description` frontmatter) plus on-demand
`references/`; Claude Code auto-activates them by description.

## Skills

| Skill | Activates when |
| --- | --- |
| `using-n8n-skills-official` | **Meta / entry point.** Load first on any n8n task; routes to the right skill and summarizes every n8n MCP tool. |
| `n8n-workflow-lifecycle-official` | Starting, designing, organizing, or shipping a workflow |
| `n8n-subworkflows-official` | Reusable, multi-step builds |
| `n8n-extending-mcp-official` | Need capabilities the MCP doesn't have |
| `n8n-expressions-official` | Writing `{{}}`, `$json`, `$node` |
| `n8n-node-configuration-official` | Configuring any node |
| `n8n-code-nodes-official` | Custom logic / Code node |
| `n8n-loops-official` | Loops, batching, paginated APIs |
| `n8n-agents-official` | LangChain Agent node, tools, structured output |
| `n8n-error-handling-official` | Webhook APIs, production workflows |
| `n8n-credentials-and-security-official` | Auth, API keys, tokens |
| `n8n-binary-and-data-official` | Files, images, attachments, vision |
| `n8n-data-tables-official` | Data Tables: schemas, dedup, persistent state |
| `n8n-debugging-official` | Things break |

## Prerequisite

An n8n instance (Cloud or self-hosted) with the instance-level MCP server
enabled. See https://docs.n8n.io/advanced-ai/mcp/accessing-n8n-mcp-server/

## How they activate here

These were installed as plain skills (not the Claude Code plugin), so the
plugin's SessionStart/PreToolUse hooks are **not** wired. Instead, `claude.md`
carries a cue telling the agent to load `using-n8n-skills-official` first on
any n8n task and route from there. To get automatic loading, install the
upstream plugin instead: `/plugin marketplace add n8n-io/skills` then
`/plugin install n8n-skills@n8n-io`.

## Source & license

- Source: https://github.com/n8n-io/skills
- Vendored at commit `9856757819847bd1ccf232925be3db0a0756b369`
- License: Apache-2.0 — see `LICENSE-n8n-skills` in this directory.

Unmodified copy of the upstream `skills/` tree. To update, re-copy from a newer
upstream commit and bump the commit hash above.
