# Web-Dev Pipeline — Cursor · Linear · Claude Code · n8n

The operating doc for running T-Ex LLM development (and any project after it) across the
user's toolchain. First tracked project: **T-Ex LLM** itself.

## 0. The bus rule (non-negotiable)

**Linear + the git repo are the bus. No AI hands off to another AI through chat.**
Every handoff is a Linear issue/comment or a committed file. A plan that lives only in a
Cursor tab or a ChatGPT window does not exist.

## 1. Lanes — one job per tool

| Tool | Lane | Output (always a file or issue) |
|---|---|---|
| ChatGPT | Web research | Research brief → issue description or `research/` |
| Cursor (5x plan) | Spec + prompt drafting, small UI edits | Build spec attached to the issue; tiny scoped diffs |
| Grok | Adversarial plan review (optional gate) | Risk/rollback/missing-steps comment on the issue |
| Claude Code (T-Ex) | **All execution** — build, deploy, verify | Code, fleet deploys, verification evidence on the issue |
| Linear | State + routing | Backlog → Todo → In Progress → In Review → Done |
| n8n | Automation layer | Webhooks in/out (see §3) — no business logic lives here |

## 2. The cycle

1. Feature → Linear issue **with acceptance checks** (runnable ones: "curl X → 200",
   "page Y renders Z"). No acceptance checks = not ready to build.
2. ChatGPT research brief if needed → attached.
3. Cursor drafts the build spec/prompt → attached.
4. (Optional gate) Grok red-teams the spec → revise until pass.
5. Claude Code executes on branch `<issue-id>-<slug>`, runs the acceptance checks,
   posts evidence, moves the issue — **Done only after run-verification**
   (`linear-integration` skill rule).
6. Bugs found later → new issue → route: UI polish → Cursor; logic/backend/deploy → Claude.

**Fast lane:** trivial fixes skip 2–4. One-line issue → straight to Cursor or Claude.

## 3. The n8n layer (webhook access)

n8n (tl-n8n box) holds the Linear API key as a **credential** — Claude never stores it.
Two workflows, shipped in `templates/n8n/`:

### 3a. `claude-gateway` — Claude → Linear (act)
- Endpoint: `POST <N8N_BASE>/webhook/tex-claude-gateway`
- Auth: header `x-tex-token: $TEX_GATEWAY_TOKEN` (env var on BOTH sides; set in the
  n8n instance env and in the calling machine's env — never in git)
- Body: raw Linear GraphQL — `{"query": "...", "variables": {...}}`
- n8n validates the token, attaches the Linear Authorization header from its stored
  credential, proxies to `https://api.linear.app/graphql`, returns Linear's response.

Claude usage example (comment on an issue):
```bash
curl -sS -X POST "$N8N_BASE/webhook/tex-claude-gateway" \
  -H "x-tex-token: $TEX_GATEWAY_TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"mutation($id:String!,$body:String!){commentCreate(input:{issueId:$id,body:$body}){success}}",
       "variables":{"id":"<issue-uuid>","body":"deploy verified: checks 3/3 pass"}}'
```

### 3b. `linear-events` — Linear → n8n (listen)
- Endpoint: `POST <N8N_BASE>/webhook/tex-linear-events` — registered in Linear
  Settings → API → Webhooks (issue + comment events).
- Ships as a receiver skeleton (respond 200, payload visible in executions); attach
  routing (notifications, queues) as needs appear — don't pre-build automations nobody asked for.
- **Reachability constraint:** Linear's cloud must reach this URL, so it needs the
  public route (cloudflared/Caddy on tl-internet). Tailnet-only n8n = 3a works
  (Claude is inside the tailnet), 3b does not.

### Claude's two Linear paths — when to use which
- **Linear MCP** (interactive sessions): rich issue tools, OAuth per profile (`/mcp`).
- **Gateway webhook** (automation/headless/hooks): fire-and-forget curl, no OAuth in
  the loop, works from any fleet box.

## 4. Linear conventions

- Project: **T-Ex LLM** (bootstrap: `scripts/linear-bootstrap.sh` — creates project,
  labels, seeds the starting backlog with acceptance checks).
- Branch naming: `<issue-id>-<slug>` (e.g. `tex-12-port-outbound-skills`) — autolinks.
- Labels: `bug` `feature` `deploy` `research` `spec` `blocked-gate`.
- Every issue body ends with `## Acceptance checks` — a checklist of runnable checks.
- Claude moves issues; Cursor comments specs; humans decide priority.

## 5. Bring-up checklist (state as of 2026-07-22)

- [x] Linear MCP registered in both Claude profiles (main + claude-web) — needs one-time `/mcp` OAuth each
- [x] Workflows authored: `templates/n8n/claude-gateway.workflow.json`, `linear-events.workflow.json`
- [x] Bootstrap script authored: `scripts/linear-bootstrap.sh` (needs `LINEAR_API_KEY`)
- [ ] tl-n8n powered on → import workflows, set `TEX_GATEWAY_TOKEN`, store Linear key as credential — Claude does this over SSH
- [ ] Public webhook route for 3b via tl-internet (only if Linear→n8n events wanted)
- [ ] Bootstrap run → project + seeded backlog exist in Linear
- [ ] Roundtrip proven: gateway curl creates a comment on a real issue (the done-gate)

## Done-gates

- Gateway proven with a real roundtrip (curl → comment visible in Linear), not assumed.
- Linear key exists ONLY as an n8n credential + (optionally) `.env` on the machine that
  runs the bootstrap once. Never in git, never in a chat.
- Every seeded issue has acceptance checks.
- The workflows' import is live-verified in the n8n UI (hand-authored JSON — verify on import).
