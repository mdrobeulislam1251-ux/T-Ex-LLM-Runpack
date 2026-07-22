---
name: linear-integration
description: Use when connecting the runpack to Linear for project management — creating and updating issues from terminal sessions, mapping build/fix cycles to issue states, branch naming from issue IDs, and the rule that an issue reaches Done only after run-verification. Covers Linear MCP setup and the GraphQL API fallback.
---

# Linear Integration

Linear is the delivery ledger: every build/fix cycle maps to an issue, and state transitions are EARNED by verification, not claimed. Chat is not an audit trail — the issue is.

## Connect — two ways, probe which fits

**1. MCP (interactive terminals — preferred):**

```sh
claude mcp add --transport sse linear https://mcp.linear.app/sse
claude mcp list        # expect: linear ... connected (first use opens browser OAuth)
```

Linear's issue tools then appear in-session (list/create/update issues, comments). Works the same whether Claude Code runs on an API key or a Max subscription — MCP auth is Linear-side OAuth.

**2. GraphQL API (headless, CI, scripts):** env var `LINEAR_API_KEY` (Linear → Settings → Security & access → Personal API keys). Probe (PS 5.1: `curl.exe`):

```sh
curl -sS https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" -H 'Content-Type: application/json' \
  --data '{"query":"{ viewer { id name } }"}'
```

Healthy: JSON containing your viewer name. Note: personal API keys go in the `Authorization` header RAW — `Bearer` prefix is for OAuth tokens only; mixing them up is the #1 "Authentication required" cause.

| Output | Fix |
|---|---|
| `Authentication required` / `AUTHENTICATION_ERROR` | Key missing, revoked, or Bearer-prefixed a personal key (or vice versa) — regenerate and match the header style |
| `RATELIMITED` | Back off and batch mutations — don't hammer per-row |

## Core GraphQL operations

```sh
# teams + their IDs (needed for everything else)
--data '{"query":"{ teams { nodes { id key name } } }"}'

# workflow states of a team (issueUpdate needs a stateId, not a name)
--data '{"query":"query($t: String!){ team(id: $t){ states { nodes { id name type } } } }","variables":{"t":"<team-id>"}}'

# create an issue
--data '{"query":"mutation($in: IssueCreateInput!){ issueCreate(input: $in){ success issue { identifier url } } }","variables":{"in":{"teamId":"<team-id>","title":"...","description":"..."}}}'

# move an issue
--data '{"query":"mutation($id: String!, $in: IssueUpdateInput!){ issueUpdate(id: $id, input: $in){ success } }","variables":{"id":"<issue-id>","in":{"stateId":"<state-id>"}}}'
```

State TYPES are stable even when teams rename states: `backlog`, `unstarted`, `started`, `completed`, `canceled` — resolve the team's actual state IDs by type, never hardcode state names.

## Workflow doctrine

- **1 issue = 1 unit of work = 1 branch.** Branch name starts with the issue identifier (`eng-123-fix-login-loop`) — Linear autolinks the branch and PR to the issue.
- State transitions are earned:
  - → `started` when the branch exists and work actually began
  - → in-review when the PR is open AND the runpack review gate owner is named
  - → `completed` ONLY after `verification-gates` passed — merge alone is "compiled, not verified"
- Blockers become a comment on the issue naming exactly what's needed and from whom — same batched-ask rule as `project-bootstrap`.
- Estimates and priorities come from the user/PM. Never invent them.

## Runpack event mapping

| Runpack event | Linear action |
|---|---|
| `/build <feature>` starts | Create/claim the issue, move to `started` |
| A review gate passes (CTO, design, QA) | Comment the gate verdict on the issue |
| `verification-gates` pass | Move to `completed` + one evidence line (what ran, what proved it) |
| `/fix <bug>` triage | Bug issue with repro steps + severity label |
| Blocked | Comment the blocker; keep state honest (don't park in `started` for days silently) |

## Done-gates

- **Integration done** = the viewer probe returns your identity AND one test issue was created and transitioned via MCP/API, then archived — not "the key is in .env".
- **Any sync claim done** = the issue actually shows the state your report claims. Check the issue, not your memory.
