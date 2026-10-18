# T-Ex LLM — Quickstart (open source)

One project: **host API + web console + team runners + optional local terminal AI CLIs**.

No vendor lock-in. No assumed personal machine paths. Works on **macOS**, **Linux/Ubuntu**, and **Windows** (WSL2 recommended; native PowerShell supported with extra notes).

---

## What this project actually does

| Mode | Needs API key? | What runs |
|------|----------------|-----------|
| **Mock team runner** | No | Built-in planner → executor → reviewer (offline demo) |
| **OpenAI-compatible HTTP** | Yes (`LLM_API_KEY`) | Same team runner via any compatible endpoint |
| **Local terminal CLI** | No (uses CLI’s own login) | Auto-detects tools on `PATH` (Claude Code, Codex, Gemini, …) and can **spawn** supported CLIs from the host |
| **Web UI** | No (optional `HOST_API_KEY`) | SPA served from the same process by default |
| **Interactive TUI** | Depends on the CLI | Use your installed agent in a real terminal against this repo; T-ex is not a full terminal emulator |

### Honest limits

- Local CLI **spawn** only works for agents that support non-interactive prompts (e.g. `claude -p`). Detected-but-interactive tools still appear in `/v1/agents` with `noninteractive: false`.
- Auth for Claude/Codex/etc. is **their** login (`claude auth login`, etc.), not `LLM_API_KEY`.
- Job storage is **in-memory** in the MVP (restart clears jobs). Postgres/Supabase hooks are setup-time detection + UI settings, not full durability yet.

---

## Requirements

| Tool | Version | Notes |
|------|---------|--------|
| Python | 3.9+ | Host + runners |
| Node.js + npm | 20+ | Build web UI once |
| Git | any | Clone |
| Optional | Docker, Tailscale, `psql` | Remote access / DB |

---

## Single setup (all platforms)

From the repository root:

```bash
git clone https://github.com/mdrobeulislam1251-ux/T-Ex-LLM-Runpack.git
cd T-Ex-LLM-Runpack/runtime
bash scripts/setup.sh
```

You will be prompted for:

- **HTTP port** (default **`3006`**)
- **API key** (default `change-me` for local demos)

Non-interactive:

```bash
bash scripts/setup.sh --port 3006 --api-key "your-secret" --non-interactive
```

Custom port:

```bash
bash scripts/setup.sh --port 8088
```

### Start

```bash
set -a && source .env && set +a   # bash/zsh
source .venv/bin/activate   # created by setup.sh (Git Bash: .venv/Scripts/activate)
python -m texllm.cli serve
```

Open:

```text
http://127.0.0.1:3006/
```

(or your chosen port)

---

## macOS

1. Install Xcode CLT if needed: `xcode-select --install`
2. Install Python 3 and Node via [Homebrew](https://brew.sh) (optional but common):
   ```bash
   brew install python node
   ```
3. Clone and setup:
   ```bash
   git clone https://github.com/mdrobeulislam1251-ux/T-Ex-LLM-Runpack.git
   cd T-Ex-LLM-Runpack/runtime
   bash scripts/setup.sh --port 3006
   source .env
   source .venv/bin/activate   # created by setup.sh (Git Bash: .venv/Scripts/activate)
   python -m texllm.cli serve
   ```
4. Optional local agents (examples — install only what you use):
   ```bash
   # Claude Code, Codex, etc. — follow each vendor’s install docs
   which claude codex gemini
   python3 -m texllm.cli agents
   ```
5. If a GUI app cannot see Homebrew binaries, ensure PATH includes `/opt/homebrew/bin` or `/usr/local/bin` for the shell that starts T-ex.

---

## Linux / Ubuntu

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git curl
# Node 20+ (example: NodeSource or distro packages)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

git clone https://github.com/mdrobeulislam1251-ux/T-Ex-LLM-Runpack.git
cd T-Ex-LLM-Runpack/runtime
bash scripts/setup.sh --port 3006
set -a && source .env && set +a
source .venv/bin/activate   # created by setup.sh (Git Bash: .venv/Scripts/activate)
python -m texllm.cli serve
```

Open firewall only if you intend LAN access (see [REMOTE-ACCESS.md](./REMOTE-ACCESS.md)):

```bash
# Ubuntu ufw example — only if required
sudo ufw allow 3006/tcp
```

---

## Windows

### Recommended: WSL2 (Ubuntu)

1. Install WSL2 + Ubuntu from Microsoft Store.
2. Inside Ubuntu, follow **Linux / Ubuntu** steps above.
3. Browser on Windows: `http://127.0.0.1:3006/` (WSL forwards localhost).

### Native PowerShell

1. Install [Python 3](https://www.python.org/downloads/) and [Node.js](https://nodejs.org/) with “Add to PATH”.
2. Open PowerShell:

```powershell
git clone https://github.com/mdrobeulislam1251-ux/T-Ex-LLM-Runpack.git
cd T-Ex-LLM-Runpack/runtime
# Git Bash or:
bash scripts/setup.sh --port 3006
# If bash unavailable:
python -m pip install -e ".[dev]"
cd apps/web; npm install; npm run build; cd ../..
# Create .env with HOST_PORT=3006 SERVE_WEB=true
python -m texllm.cli serve
```

3. Local CLI agents on Windows use **Windows** PATH and credential stores; WSL agents are separate installs.

---

## Execution modes after install

### 1) Detect terminal AI CLIs

```bash
python3 -m texllm.cli agents
# or
curl -s http://127.0.0.1:3006/v1/agents -H "X-API-Key: change-me"
```

### 2) Spawn a local CLI (uses CLI login, not LLM_API_KEY)

```bash
python3 -m texllm.cli spawn claude "Summarize the T-ex LLM README in 5 bullets"
```

HTTP:

```bash
curl -s -X POST http://127.0.0.1:3006/v1/agents/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d '{"agent_id":"claude","prompt":"Say hello from local CLI"}'
```

### 3) Team runner (mock / API)

```bash
python3 -m texllm.cli run "List three benefits of multi-agent workers" --provider mock
```

### 4) Interactive TUI (your terminal)

```bash
cd /path/to/T-Ex-LLM-Runpack/runtime
claude    # or codex, gemini, …
# Point the agent at playbooks/ and skills/ in this repo
```

### 5) Capability report

```bash
curl -s http://127.0.0.1:3006/v1/system
```

---

## Port and environment

| Variable | Default | Meaning |
|----------|---------|---------|
| `HOST_PORT` | `3006` | HTTP port (API + web) |
| `HOST_BIND` | `0.0.0.0` | Listen address |
| `HOST_API_KEY` | `change-me` | API auth when not left as default |
| `SERVE_WEB` | `true` | Serve `apps/web/dist` from host |
| `ALLOW_LOCAL_CLI` | `true` | Permit backend CLI spawn |
| `LLM_PROVIDER` | `auto` | `auto` / `mock` / `openai` |
| `LLM_API_KEY` | empty | Only for OpenAI-compatible mode |
| `LLM_BASE_URL` | vendor URL | OpenAI-compatible base |

```bash
texllm serve --port 4000
# equivalent
HOST_PORT=4000 python3 -m texllm.cli serve
```

---

## Remote / private access

See **[REMOTE-ACCESS.md](./REMOTE-ACCESS.md)** for:

- LAN / private IP
- Tailscale
- Public domain with DNS **A** record + reverse proxy / TLS

---

## Project layout (operators)

```text
scripts/setup.sh          # single setup entry
texllm/                   # host, workers, CLI agent detect/spawn
apps/web/                 # web console source
firmware/                 # versioned agent packages
playbooks/                # tool-agnostic instructions for any agent
skills/                   # skill packs
docs/                     # this guide + remote access
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Web 404 / blank | Re-run `cd apps/web && npm run build` then restart serve |
| Port in use | `bash scripts/setup.sh --port 3010` or free the port |
| No agents detected | Install a CLI and ensure its `bin` is on `PATH` for the process running T-ex |
| Claude spawn 401 | Run `claude auth login` in the same OS user environment |
| macOS GUI missing PATH | Start serve from a login shell or fix PATH for launch agents |
| Windows vs WSL | Install and authenticate CLIs in the same environment that runs the host |

---

## License

Apache-2.0 — see [LICENSE](../LICENSE).
