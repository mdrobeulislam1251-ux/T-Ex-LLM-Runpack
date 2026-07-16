# T-ex LLM

**Portable multi-agent AI platform** — team runners, host runtime, and sellable agentic firmware for apps and products. Works with **Grok**, **Claude Code**, **Codex**, OpenAI-compatible APIs, or offline **mock** mode.

## Status

MVP runtime is live in this repo:

| Layer | Status |
|-------|--------|
| Team workers (plan → execute → review → integrate) | Done |
| Host API (jobs, firmware list, health) | Done |
| Sample firmware `sample-assistant@0.1.0` | Done |
| Mock + OpenAI-compatible providers | Done |
| Tool registry + allowlists | Done |
| Durable queue / multi-tenant prod | Roadmap |

## Quick start

```bash
git clone https://github.com/mdrobeulislam1251-ux/T-ex-LLM.git
cd T-ex-LLM
python3 -m pip install -e ".[dev]"
```

### Run a team job offline (no API key)

```bash
export LLM_PROVIDER=mock
python3 -m texllm.cli "Explain how to sell agentic firmware in a SaaS product"
# or
python3 examples/run_demo.py "Your goal here"
```

### Run the host API

```bash
export LLM_PROVIDER=mock
export HOST_API_KEY=dev-secret
python3 -m texllm.host.app
# → http://0.0.0.0:8080
```

```bash
# health
curl -s http://127.0.0.1:8080/health

# create job
curl -s -X POST http://127.0.0.1:8080/v1/jobs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret" \
  -d '{"goal":"List benefits of multi-agent workers","firmware_id":"sample-assistant","firmware_version":"0.1.0"}'

# poll (use job id from create)
curl -s http://127.0.0.1:8080/v1/jobs/<JOB_ID> -H "X-API-Key: dev-secret"
```

### Use a real model (OpenAI-compatible)

```bash
cp .env.example .env
# set LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
export LLM_PROVIDER=openai
# Examples:
#   OpenAI:  LLM_BASE_URL=https://api.openai.com/v1
#   xAI:     LLM_BASE_URL=https://api.x.ai/v1   LLM_MODEL=grok-...
#   Local:   LLM_BASE_URL=http://127.0.0.1:11434/v1
python3 -m texllm.cli "Draft an onboarding agent for our CRM"
```

### Tests

```bash
LLM_PROVIDER=mock python3 -m pytest -q
```

## Architecture

```
Customer apps  →  Integrate (SDK/webhooks)
                      ↓
              Firmware packages (versioned)
                      ↓
              Host API (jobs, auth)
                      ↓
         Team runners: planner → executor → reviewer → integrator
                      ↓
         Providers (mock | OpenAI-compat) + tools
```

See [docs/architecture.md](./docs/architecture.md).

## Repo layout

```
texllm/                 # Python package (host, workers, providers, firmware loader)
firmware/sample-assistant/   # Demo agentic firmware
playbooks/              # Tool-agnostic playbooks (any terminal AI)
skills/                 # Skill packs for Grok / adapters
examples/               # Demos
tests/                  # Pytest suite
```

## Playbooks (any terminal AI)

| Intent | File |
|--------|------|
| Route work | `playbooks/00-orchestrator.md` |
| Host / deploy | `playbooks/01-host.md` |
| Team workers | `playbooks/02-workers.md` |
| ML / evals | `playbooks/03-ml-engineer.md` |
| Firmware packages | `playbooks/04-firmware.md` |
| Product integrate | `playbooks/05-integrate.md` |

Point **Grok / Claude Code / Codex** at this repo and load the matching playbook or `skills/*/SKILL.md`.

## Agentic firmware

Ship agents as versioned packages:

```
firmware/<id>/
  manifest.yaml
  prompts/
  tests/
  README.md
```

Create a new package by copying `firmware/sample-assistant/` and editing prompts + tools.

## API (host)

| Method | Path | Notes |
|--------|------|--------|
| GET | `/health` | Liveness |
| GET | `/v1/firmware` | List packages |
| POST | `/v1/jobs` | Create job (`goal`, `firmware_id`, `firmware_version`) |
| GET | `/v1/jobs/{id}` | Poll status + result |
| GET | `/v1/jobs` | Recent jobs |
| POST | `/v1/jobs/{id}/cancel` | Cancel if still queued |

Auth: header `X-API-Key` (required when `HOST_API_KEY` is not the default `change-me`).

## Principles

1. **Model-agnostic** — swap providers via env.
2. **Worker-first** — team runners over a single free-form agent.
3. **Firmware as product** — versioned packages with I/O contracts.
4. **Terminal + API** — same runners for CLI and host.

## License

Apache-2.0 — see [LICENSE](./LICENSE).
