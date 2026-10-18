# T-ex LLM Architecture

## Goals

- **Accurate multi-agent work** via team-based runners (not a single free-form chat agent).
- **Host server** that schedules, isolates, and observes workers.
- **Firmware** — versioned agent packages customers embed in apps/platforms.
- **Model-agnostic** — OpenAI-compatible APIs, Grok, Claude, local models, etc.

## Logical layers

```
┌─────────────────────────────────────────────────────────┐
│  Customer apps / platforms (Integrate layer)            │
└───────────────────────────┬─────────────────────────────┘
                            │ SDK / webhooks / embed
┌───────────────────────────▼─────────────────────────────┐
│  Firmware packages (roles, tools, policies, prompts)    │
└───────────────────────────┬─────────────────────────────┘
                            │ load / version pin
┌───────────────────────────▼─────────────────────────────┐
│  Host runtime (API, queue, auth, observability)         │
│         │                                               │
│         ▼                                               │
│  Workers / team runners (planner, executor, reviewer…)  │
└───────────────────────────┬─────────────────────────────┘
                            │ tool calls / model calls
┌───────────────────────────▼─────────────────────────────┐
│  ML / model providers + tools + memory + evals          │
└─────────────────────────────────────────────────────────┘
```

## Team runner pattern (preferred)

1. **Orchestrator** — decomposes the job, assigns roles.
2. **Specialists** — parallel or sequential workers with narrow tools.
3. **Reviewer / verifier** — checks outputs against acceptance criteria.
4. **Integrator** — packages results for host API or customer app.

Prefer explicit handoffs and shared state over one giant context window.

## Open-source influences (reference only)

When implementing, draw patterns from (do not vendor lock):

- Multi-agent graphs / crews (LangGraph, CrewAI-style role teams)
- Durable job runners (Temporal-style workflows, queue workers)
- Agent frameworks with tool registries and eval loops

Document any direct dependency and its license before adding code.
