# T-ex LLM

Open-source multi-agent host: **team runners**, **web console**, and **local terminal AI CLI detection/spawn**.

Apache-2.0 · single setup · default port **3006**

## Honest feature matrix

| Capability | Status |
|------------|--------|
| Team runner (plan → execute → review → integrate) | Working |
| Mock provider (no API key) | Working |
| OpenAI-compatible HTTP provider | Working |
| Auto-detect agent CLIs on PATH | Working |
| Spawn local CLI from host (e.g. `claude -p`) | Working when CLI supports non-interactive mode + is logged in |
| Web UI + API on one port | Working (`SERVE_WEB=true`) |
| Interactive TUI inside the browser | Not this project — use Claude/Codex/etc. in a real terminal |
| Durable Postgres job store | Not yet (in-memory jobs) |

Local CLIs use **their own auth** (e.g. `claude auth login`). That is separate from `LLM_API_KEY`.

## Quick start

```bash
git clone https://github.com/mdrobeulislam1251-ux/T-ex-LLM.git
cd T-ex-LLM
bash scripts/setup.sh          # prompts for port (default 3006)
set -a && source .env && set +a
python3 -m texllm.cli serve
```

Open **http://127.0.0.1:3006/**

Full multi-OS guide: **[docs/QUICKSTART.md](./docs/QUICKSTART.md)**  
Tailscale / LAN / DNS A-record: **[docs/REMOTE-ACCESS.md](./docs/REMOTE-ACCESS.md)**  
**Multi-team workspace:** **[docs/WORKSPACE.md](./docs/WORKSPACE.md)** (`tex` / `@T-ex`)  
**Claude-first:** **[docs/CLAUDE-FIRST.md](./docs/CLAUDE-FIRST.md)** · Auth: **[docs/AUTH.md](./docs/AUTH.md)**

```bash
# Custom port
bash scripts/setup.sh --port 8088 --non-interactive
python3 -m texllm.cli serve --port 8088
```

## Useful commands

```bash
# Multi-team workspace (shared DB with web UI)
tex teams
tex dash sales
tex run ops "Stabilize onboarding SLA"
tex review example.com
tex bd "Partnership plan"
tex @T-ex "Weekly CEO priorities"
# or: python3 -m texllm.tex_cli teams

python3 -m texllm.cli agents
python3 -m texllm.cli serve   # web + API :3006
```

## Layout

```text
scripts/setup.sh     single installer (macOS / Linux / Ubuntu / Windows via bash)
texllm/              host, workers, CLI detect & spawn
apps/web/            operator console
firmware/            versioned agent packages
playbooks/           instructions for any terminal agent
docs/                quickstart + remote access
```

## License

Apache-2.0 — see [LICENSE](./LICENSE).
