# Provider authentication for T-ex LLM

How “native OAuth / session tokens” work (OpenClaw-style), what is **allowed**, and how T-ex should integrate.

---

## Short answer

| Approach | Works for | Like OpenClaw? | Recommended for T-ex |
|----------|-----------|----------------|----------------------|
| **API key** (official) | Claude API, OpenAI Platform, xAI Grok, Gemini API | Partial | **Yes — primary** |
| **Local CLI session** (reuse logged-in CLI) | Claude Code, Codex, Gemini CLI on the **same host** | Yes (Claude CLI reuse) | **Yes — primary for “no API key”** |
| **Vendor OAuth into *our* app** (user signs in with Claude/ChatGPT in the browser, we get a token to call their chat subscription) | Mostly **not** offered as a public third-party product OAuth for billing-on-subscription | What people wish OpenClaw still did freely | **Generally no** (ToS / blocked) |
| **Google OAuth** for Gemini / Vertex | Google Cloud / AI Studio projects you own | Real OAuth | **Yes — when you configure GCP client** |
| **Browser cookie / scraped session** | Unofficial | Some community tools | **No — do not ship** |

OpenClaw’s “subscription OAuth” is not a free-for-all “Login with Claude” SDK for every app. In practice it is:

1. **OpenAI Codex / ChatGPT OAuth** where OpenAI exposes that surface for Codex-style runtimes  
2. **Anthropic Claude CLI reuse** — host already has `claude` logged in; tools spawn `claude -p` or reuse CLI-managed tokens  
3. **API keys** for normal pay-per-token usage  

Anthropic has also tightened rules: **consumer Pro/Max OAuth tokens are for Claude.ai / Claude Code**, not for third-party harnesses that call the API as if they were Claude Code. Treat “paste Max OAuth into our product” as **non-compliant** and fragile.

---

## Per-provider reality (2026)

### Claude (Anthropic)

| Method | Notes |
|--------|--------|
| **API key** (`sk-ant-…`) | Official for apps and agents. Console billing. |
| **Claude Code CLI login** | Session lives on the machine (`claude auth login`). T-ex already **detects/spawns** `claude`. |
| **Reuse OAuth token in our HTTP client** | Risky / often ToS-restricted for third-party products. Prefer CLI spawn or API key. |

**T-ex path:** Settings → “Use local Claude CLI session” + `POST /v1/agents/run` with `agent_id=claude`.

### ChatGPT / OpenAI

| Method | Notes |
|--------|--------|
| **Platform API key** | Official for your app’s backend. |
| **Codex CLI / ChatGPT OAuth** | OpenClaw-style: Codex runtime + OAuth for subscription Codex — **not** the same as “any app uses Plus quota via OAuth.” |
| **Login with ChatGPT for our SaaS** | OpenAI does **not** generally let third-party UIs bill against a user’s Plus subscription for free. |

**T-ex path:** `LLM_API_KEY` + OpenAI-compatible provider, and/or local `codex` CLI if installed.

### Grok (xAI)

| Method | Notes |
|--------|--------|
| **API key** + base URL | Standard for third-party apps. |
| **Native OAuth for third-party** | Not a general “Login with Grok subscription” for arbitrary agents. |

**T-ex path:** `LLM_BASE_URL=https://api.x.ai/v1` + `LLM_API_KEY`.

### Gemini (Google)

| Method | Notes |
|--------|--------|
| **API key** (AI Studio) | Simple. |
| **Google OAuth / service account** | Real OAuth 2.0 / ADC for Vertex AI — **this is the only major vendor where classic OAuth into *your* cloud project is first-class**. |

**T-ex path:** API key now; optional Google OAuth client for Vertex later.

---

## Architecture T-ex should use (OpenClaw-like, compliant)

```
┌─────────────────────────────────────────────────────────┐
│  Web UI  Settings → Auth profiles                        │
└───────────────────────┬─────────────────────────────────┘
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
   API key vault   CLI session    OAuth (Google only
   (encrypted)     status probe   when configured)
         │              │              │
         └──────────────┼──────────────┘
                        ▼
              Provider router
         mock | openai_compat | local_cli
```

### Profile types

```json
{
  "profiles": [
    {
      "id": "openai-key",
      "provider": "openai",
      "method": "api_key",
      "label": "OpenAI Platform"
    },
    {
      "id": "claude-cli",
      "provider": "anthropic",
      "method": "local_cli",
      "agent_id": "claude",
      "label": "Claude Code session on this host"
    },
    {
      "id": "xai-key",
      "provider": "xai",
      "method": "api_key",
      "base_url": "https://api.x.ai/v1"
    },
    {
      "id": "gemini-key",
      "provider": "gemini",
      "method": "api_key"
    }
  ],
  "default_profile_id": "claude-cli"
}
```

Secrets (API keys, refresh tokens) stay **on the host** (`.texllm/credentials.json` with restricted permissions, or OS keychain later) — never commit to git, never send to the browser after save.

### Session tokens vs API keys

| Term | Meaning in T-ex |
|------|-----------------|
| **API key** | Long-lived secret you paste; HTTP `Authorization: Bearer` |
| **CLI session** | Tokens managed by Claude/Codex/Gemini CLI after `login`; we **do not copy** them; we **spawn** the CLI or read *status only* |
| **OAuth access token** | Short-lived; refresh with refresh_token; only for flows we implement officially (e.g. Google) |

We **do not** implement “paste session cookie from chat.openai.com / claude.ai”.

---

## User flows

### A) API key (all vendors)

1. Settings → Auth profiles → Add key  
2. Host stores encrypted/local secret  
3. Team runner uses OpenAI-compatible client with that base URL + key  

### B) Local CLI session (Claude / Codex / Gemini CLI) — closest to OpenClaw

1. User installs CLI and runs vendor login on the **same machine as T-ex host**  
2. `GET /v1/agents` shows detected CLI + version  
3. Optional: `GET /v1/auth/cli-status` runs `claude auth status` (etc.)  
4. Jobs/chat route to `local_cli` spawn with aliases preamble  

### C) Google OAuth (Gemini / Vertex) — real OAuth

1. Operator registers Google Cloud OAuth client (or uses service account)  
2. User opens `/v1/auth/google/start` → Google consent → callback stores tokens  
3. Host refreshes access tokens and calls Vertex/Gemini APIs  

---

## Security rules

1. Never log full tokens  
2. `HOST_API_KEY` protects credential write endpoints  
3. `ALLOW_LOCAL_CLI=false` on multi-tenant public hosts  
4. Prefer OS user isolation: one T-ex host per operator machine for CLI sessions  
5. Document ToS: subscription OAuth hijacking is out of scope  

---

## What T-ex has today

| Feature | Status |
|---------|--------|
| OpenAI-compatible API keys | Yes (`LLM_*` env) |
| Local CLI detect + spawn | Yes (`/v1/agents`, `/v1/agents/run`) |
| Auth profiles UI + encrypted vault | Scaffold / roadmap (`/v1/auth/profiles`) |
| ChatGPT/Claude browser OAuth into our product | **Out of scope** (not offered / restricted) |
| Google OAuth | Roadmap |

---

## Operator checklist

```bash
# 1) Prefer local sessions when you already pay for Claude Code / Codex
claude auth status --text
python3 -m texllm.cli agents
python3 -m texllm.cli spawn claude "ping"

# 2) Or use official API keys
export LLM_PROVIDER=openai
export LLM_BASE_URL=https://api.anthropic.com/v1   # if using compatible gateway
export LLM_API_KEY=sk-...

# 3) xAI example
export LLM_BASE_URL=https://api.x.ai/v1
export LLM_API_KEY=xai-...
export LLM_MODEL=grok-...
```

See also: [QUICKSTART.md](./QUICKSTART.md), [REMOTE-ACCESS.md](./REMOTE-ACCESS.md).
