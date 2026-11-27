# App Dev and Engineering Team

Track owning the **core agent execution engines, runtime hooks, and system
deployments** of the Arion multi-agent workspace.

Arion routes any task query whose keywords match this track's routes here.

| Workspace       | Purpose                                                    | Trigger keywords (excerpt)                     |
| --------------- | ---------------------------------------------------------- | ---------------------------------------------- |
| `agents/`       | Agent execution engines & orchestration logic              | agent, sub-agent, execution engine, orchestrator |
| `runtime_hooks/`| Runtime hooks, lifecycle interceptors, event middleware    | hook, runtime, trigger, event, middleware      |
| `deployments/`  | System deployments via Tailnet SSH (tl-host) + Playwright  | deploy, ssh, tailnet, tl-host, playwright      |

The authoritative keyword map lives in [`config/routing.json`](../config/routing.json).
Do not edit trigger keywords here — this table is documentation only.
