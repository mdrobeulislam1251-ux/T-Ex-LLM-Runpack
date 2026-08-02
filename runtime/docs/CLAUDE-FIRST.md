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
# not mock (unless nothing configured)
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| mock replies | No default Claude profile — connect Max token or CLI or API key |
| `claude CLI not found` | Install Claude Code; fix PATH for the process running `texllm serve` |
| CLI 401 / auth | `claude auth login` or refresh setup-token |
| Chat error 502 | Read `detail` in response; fix Claude auth on host |
