# Playbook: ML-native AI engineer

Design agents that are **reliable**, not just chatty.

## Focus areas

- Provider abstraction (OpenAI-compatible + vendor SDKs)
- Tool design (typed I/O, side-effect safety)
- Memory (short-term job state + optional long-term store)
- Routing (cheap model for plan, strong model for hard steps)
- Evals (golden tasks, regression suite)
- Guardrails (PII, tool allowlist, output schema validation)

## Implementation checklist

1. `providers/` interface: `complete`, `stream`, optional embeddings.
2. Tool registry with JSON schema validation.
3. Structured outputs for handoffs between workers.
4. Eval harness under `examples/evals/` or `tests/evals/`.
5. Document model env: `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`.

## Acceptance criteria

- Swap providers via env without code changes for MVP path.
- At least one eval suite that fails on broken prompts/tools.
- Tools reject invalid args before side effects.
