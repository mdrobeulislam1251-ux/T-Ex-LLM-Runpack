# How NanoClaw / OpenClaw / AionUi do “subscription auth” — and how T-ex matches it

This is product research mapped into **T-ex LLM**, not theory.

---

## What you asked for

Same as NanoClaw:

| Account type | Goal |
|--------------|------|
| **Claude Max / Pro** | Use flat subscription, not only pay-per-token API |
| **ChatGPT account** | Codex / ChatGPT subscription path |
| **Gemini subscription** | Google account / AI access |
| **API keys** | Always available as fallback |

---

## How those projects actually do it

### [NanoClaw](https://nanoclaw.dev) · [github.com/nanocoai/nanoclaw](https://github.com/nanocoai/nanoclaw)

From their site + README:

1. **Native runtime = Claude Agent SDK / Claude Code** (not a random HTTP wrapper only).
2. Installer `nanoclaw.sh` **registers your Anthropic credential with OneCLI** (credential vault).
3. Agents run in **containers**; **agents never hold raw keys** — vault injects auth on outbound HTTPS.
4. Claude auth options users document:
   - **Subscription:** `claude setup-token` (long-lived OAuth-style material for Max/Pro)
   - **API key:** `ANTHROPIC_API_KEY=sk-ant-…`
5. Other providers as drop-ins:
   - `/add-codex` → **OpenAI Codex (ChatGPT subscription or API key)**
   - `/add-opencode` → OpenRouter / Google / DeepSeek…
   - `/add-ollama-provider` → local models

So NanoClaw is **not** “magic browser cookie scrape of claude.ai”.  
It is: **Claude Code session / setup-token / API key → vault → Agent SDK**, plus optional other CLIs.

### [OpenClaw OAuth docs](https://docs.openclaw.ai/concepts/oauth)

OpenClaw documents explicitly:

| Path | Mechanism |
|------|-----------|
| **OpenAI Codex / ChatGPT OAuth** | Real **PKCE** → `auth.openai.com/oauth/authorize` → token exchange → store `{access, refresh, expires}` |
| **Anthropic** | **Claude CLI reuse** (`claude -p`) and/or **`claude setup-token` paste** into auth profile “token sink” |
| **API keys** | Same profile store |
| Storage | Per-agent auth profiles (JSON/SQLite under `~/.openclaw/agents/...`) |

Multi-account = multiple **profiles** + routing.

### [AionUi](https://github.com/iOfficeAI/AionUi)

From FAQ / wiki:

1. **Built-in agent** → paste **API keys** (Gemini, OpenAI, Anthropic, …).
2. **Multi-Agent mode** → **auto-detect CLIs** (Claude Code, Codex, Gemini CLI, …).
3. **Each CLI keeps its own auth** (`claude login`, `qwen login`, env key, or OAuth). AionUi is a **UI + router**, not a replacement login for every vendor.

---

## How T-ex implements the same model

| NanoClaw / OpenClaw / Aion idea | T-ex |
|---------------------------------|------|
| Claude Max via setup-token | `POST /v1/auth/claude/setup-token` + Settings paste |
| ChatGPT / Codex OAuth PKCE | `POST /v1/auth/oauth/start` provider=`openai` + callback |
| Gemini / Google OAuth | `POST /v1/auth/oauth/start` provider=`google` (needs client id) |
| Local CLI already logged in | `method=local_cli` + `/v1/agents/run` + detect |
| API keys | `method=api_key` profiles |
| Token sink / vault on host | `.texllm/credentials.json` (mode 600) |
| Default profile drives runtime | `resolve_runtime()` → team runner provider factory |
| Never send secrets to browser after save | list profiles redacts secrets |

### Settings UI (connect cards)

- **Connect Claude Max** → paste `claude setup-token`
- **Connect ChatGPT / Codex** → start OAuth PKCE (or local `codex` CLI)
- **Connect Gemini** → Google OAuth or Gemini CLI / API key
- **API key** → any OpenAI-compatible / Anthropic / xAI / Gemini key
- **Use local CLI session** → AionUi-style

---

## Operator steps (same as NanoClaw spirit)

### Claude Max / Pro

```bash
# On the host that runs T-ex
claude setup-token
# paste token into Settings → Claude Max, or:
curl -s -X POST http://127.0.0.1:3006/v1/auth/claude/setup-token \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d '{"token":"PASTE_HERE","profile_id":"claude-max","set_default":true}'
```

Or reuse CLI only (AionUi style):

```bash
claude auth login
# Settings → local_cli / agent_id=claude
```

### ChatGPT account (Codex OAuth)

```bash
# Optional env (OpenClaw-style client)
export CODEX_OAUTH_CLIENT_ID=...
export CODEX_OAUTH_REDIRECT_URI=http://127.0.0.1:3006/v1/auth/oauth/codex/callback

curl -s -X POST http://127.0.0.1:3006/v1/auth/oauth/start \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d '{"provider":"openai","profile_id":"chatgpt-codex"}'
# open authorize_url in browser → callback stores tokens
```

Or: install Codex CLI, log in, use `local_cli` + `agent_id=codex`.

### Gemini

```bash
export GOOGLE_OAUTH_CLIENT_ID=...
export GOOGLE_OAUTH_CLIENT_SECRET=...
# then oauth/start provider=google
```

Or Gemini API key / `gemini` CLI login + `local_cli`.

### API key (always)

Settings → method **API key** → provider openai / anthropic / xai / gemini / custom base URL.

---

## API map

| Endpoint | Purpose |
|----------|---------|
| `GET /v1/auth/profiles` | List profiles (no secrets) |
| `PUT /v1/auth/profiles` | Upsert profile |
| `POST /v1/auth/claude/setup-token` | Claude Max setup-token |
| `POST /v1/auth/oauth/start` | Start Codex or Google PKCE |
| `GET /v1/auth/oauth/codex/callback` | Codex token exchange |
| `GET /v1/auth/oauth/google/callback` | Google token exchange |
| `GET /v1/auth/cli-status/{id}` | Is CLI logged in? |
| `GET /v1/auth/runtime` | Which profile drives jobs (redacted) |
| `POST /v1/agents/run` | Spawn local CLI with host session |

---

## Notes from the field (factual)

- NanoClaw FAQ: free software; **usage still billed via Claude API key or Claude Code subscription**.
- OpenClaw stores OAuth + API keys in a **token sink** and refreshes when `expires` passes.
- AionUi splits **built-in API keys** vs **external CLI auth ownership**.
- T-ex default port remains **3006**; credentials stay on the machine under `.texllm/`.

This is the architecture those products use. T-ex now exposes the same **product surface**: Max setup-token, ChatGPT/Codex OAuth, Gemini OAuth/CLI, and API keys together.
