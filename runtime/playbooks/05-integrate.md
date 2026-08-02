# Playbook: Platform / app integration

Integrate T-ex LLM agents into **platforms and apps you sell**.

## Integration modes

| Mode | Use when |
|------|----------|
| REST/gRPC jobs | Backend product needs async agent work |
| Webhooks | Notify app when job completes |
| Embed / iframe | Light UI inside customer product |
| SDK (TS/Python) | Product engineers call agents in-process or via host |
| CLI | Ops, demos, terminal AI workflows |

## Implementation checklist

1. Public API contract + OpenAPI (or equivalent).
2. Auth: API keys / OAuth for tenants.
3. Webhook signing + retry policy.
4. SDK stubs: create job, wait, stream events.
5. Example app under `examples/integrate-demo/`.
6. Document rate limits and data retention.

## Acceptance criteria

- External app can create a job and receive a signed completion webhook.
- SDK example runs against local host.
- Multi-tenant isolation documented and enforced at API boundary.
