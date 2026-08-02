# T-ex — the product (not a dark dashboard)

## What this is

**Company Runbook Agent:** a pre-loaded, placeholder-based full company spine from **intent → product deployment**, powered by multi-team agents and multi-provider AI.

```
Intent → Domain → Product → Teams → Build → GTM → Deploy
```

You can fill placeholders **without AI**. When ready, connect **Claude / ChatGPT / Gemini / Grok** (API key or subscription/OAuth/CLI) and **Run phase agent**.

## What this is not

- A random dark “runtime telemetry” toy
- Dashboard skin experiments as the product

(The optional ops screen lives at `/console` only.)

## Open

```
http://127.0.0.1:3006/          → Company Runbook (product)
http://127.0.0.1:3006/workspace → Team dashboards
http://127.0.0.1:3006/console   → optional runtime console
```

## Providers

| Provider | API key | Subscription / OAuth / CLI |
|----------|---------|----------------------------|
| Claude | sk-ant-… | setup-token, `claude auth login` |
| ChatGPT | OpenAI key | Codex OAuth / codex CLI |
| Gemini | AI Studio key | Google OAuth / gemini CLI |
| Grok | xAI key | API |

## CLI

```bash
tex @T-ex "Start company from intent"
tex review example.com
tex export sales
tex run ceo "Execute runbook phase product"
```

## API

- `GET /v1/runbook`
- `PATCH /v1/runbook/phases/{id}`
- `POST /v1/runbook/phases/{id}/run`
