# T-ex LLM

**Portable multi-agent AI platform** — team runners, host runtime, and sellable agentic firmware for apps and products. Works with **Grok**, **Claude Code**, **Codex**, and any LLM API.

## What this is

T-ex LLM is a model-agnostic kit for:

| Layer | Purpose |
|-------|---------|
| **Host** | Runtime, API, queues, and deploy surface for agents |
| **Workers** | Team-based runners (roles, handoffs, parallel work) |
| **ML / agent eng** | Tools, memory, evals, model routing |
| **Firmware** | Versioned agent packages you ship into products |
| **Integrate** | SDKs, webhooks, and embeds for platforms you sell |

Instructions are written as **portable playbooks** so the same repo works in any terminal AI window or direct API usage.

## Repo layout (scaffold)

```
T-ex-LLM/
├── README.md
├── LICENSE
├── .gitignore
├── docs/                 # Architecture & product docs
├── playbooks/            # Tool-agnostic agent playbooks (any CLI/API)
├── skills/               # Skill packs (Grok / Claude / Codex adapters)
│   ├── agentic-host/
│   ├── agentic-workers/
│   ├── agentic-ml-engineer/
│   ├── agentic-firmware/
│   └── agentic-integrate/
├── host/                 # Host server (to be implemented)
├── workers/              # Worker / runner runtime (to be implemented)
├── firmware/             # Agent firmware packages (to be implemented)
└── examples/             # Sample integrations
```

## Quick start

### 1. Clone

```bash
git clone https://github.com/mdrobeulislam1251-ux/T-ex-LLM.git
cd T-ex-LLM
```

### 2. Use with any terminal AI

Point your agent at this repo and load the relevant playbook:

| Goal | Open |
|------|------|
| Overall map | `playbooks/00-orchestrator.md` |
| Host / deploy | `playbooks/01-host.md` |
| Team workers | `playbooks/02-workers.md` |
| ML agent design | `playbooks/03-ml-engineer.md` |
| Product firmware | `playbooks/04-firmware.md` |
| App integration | `playbooks/05-integrate.md` |

### 3. Grok skills (optional)

If you use Grok Build / Grok CLI:

```bash
# Project-scoped skills (recommended for this repo)
mkdir -p .grok/skills
cp -R skills/* .grok/skills/
```

Claude Code / Codex: copy the same markdown bodies into `CLAUDE.md`, `AGENTS.md`, or that tool’s skill format.

## Principles

1. **Model-agnostic** — no hard dependency on a single vendor API.
2. **Worker-first** — prefer team runners over a single monolithic agent.
3. **Firmware as product** — agents ship as versioned packages with clear I/O contracts.
4. **Terminal + API** — same playbooks for human-in-the-loop CLI and automated deploy.

## Status

Early scaffold. Host, workers, and firmware runtimes will land in follow-up commits.

## License

Apache-2.0 — see [LICENSE](./LICENSE).
