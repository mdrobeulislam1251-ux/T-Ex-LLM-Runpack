# Claude-first path (only)

End-to-end: **connect Claude → Chat + Jobs use that Claude auth**.

## 1. Start host

```bash
cd T-Ex-LLM-Runpack/runtime
bash scripts/setup.sh --port 3006 --non-interactive   # once
set -a && source .env && set +a
python3 -m texllm.cli serve
# open http://127.0.0.1:3006/
```

## 2. Connect Claude (pick one)

### A) Claude Max / Pro setup-token (NanoClaw-style)

```bash
claude setup-token
```

Settings → **Claude Max / Pro** → paste token → **Save**.

Or API:

```bash
curl -s -X POST http://127.0.0.1:3006/v1/auth/claude/setup-token \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d '{"token":"PASTE","set_default":true}'
```

Requires `claude` CLI on the **same machine** as the host (token injected as `CLAUDE_CODE_OAUTH_TOKEN` for `claude -p`).

### B) Local Claude Code login

```bash
claude auth login
```

Settings → **Use local Claude CLI**, or:

```bash
curl -s -X POST http://127.0.0.1:3006/v1/auth/claude/use-cli \
  -H "X-API-Key: change-me" -H "Content-Type: application/json" \
  -d '{}'
```

### C) Anthropic API key (`sk-ant-…`)

Settings → **API key** → provider Anthropic → paste key → Save.

## 3. Verify

```bash
curl -s http://127.0.0.1:3006/v1/auth/runtime -H "X-API-Key: change-me"
curl -s -X POST http://127.0.0.1:3006/v1/chat \
  -H "Content-Type: application/json" -H "X-API-Key: change-me" \
  -d '{"message":"Say hello in one short sentence"}'
```

## 4. Use product

| UI | What runs |
|----|-----------|
| **Chat** | `POST /v1/chat` → Claude (CLI or API) |
| **Jobs → Run team** | Team runner → same Claude provider for each role |

## 5. Check runtime

```bash
curl -s http://127.0.0.1:3006/v1/auth/runtime -H "X-API-Key: change-me"
# expect method: setup_token | local_cli | api_key
# "mock" only if you explicitly set LLM_PROVIDER=mock; with nothing
# configured, runs fail with an actionable error instead of mock drafts
```

## Agent sessions (chat mode)

With a Claude setup-token or CLI login connected, every chat-mode team run
executes as a full headless Claude Code session (like NanoClaw), not a
single-shot completion. Sessions run in the team's persistent memory dir
(`.texllm/teams/<slug>/`): `CLAUDE.md` there is regenerated from the team's
brains/skills each run, and the agent keeps its own durable notes in
`notes.md`. Disable with `CHAT_AGENT_SESSIONS=false`. API-key-only and
`LLM_PROVIDER=mock` setups keep the single-shot loop.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `No AI provider configured` errors | Connect Max token, CLI, or API key (mock is opt-in via `LLM_PROVIDER=mock`) |
| `claude CLI not found` | Install Claude Code; fix PATH for the process running `texllm serve` |
| CLI 401 / auth | `claude auth login` or refresh setup-token |
| Chat error 502 | Read `detail` in response; fix Claude auth on host |
