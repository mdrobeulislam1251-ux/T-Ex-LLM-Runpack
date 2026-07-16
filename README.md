# Arion-Multi-Agent

**Arion** is the Global Workspace Assistant brain: a keyword-triggered,
multi-agent router that dispatches task queries to the sub-agent workspace
that owns them. Built test-first (see [`tasks.md`](tasks.md)) with a
zero-dependency Python core.

## Two-track architecture

| Track                              | Owns                                                    |
| ---------------------------------- | ------------------------------------------------------- |
| **App Dev and Engineering Team/**  | Agent execution engines, runtime hooks, deployments     |
| **Robeul's Workspace Assistant/**  | Task management, external tool handlers, support pipelines |

Full tree and routing schema: [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Quick start

```bash
# Route a task query to its owning workspace
python3 arion.py route "deploy the agent to tl-host over tailnet via ssh"
python3 arion.py route "check my gmail and update asana"

# Inspect configuration
python3 arion.py list       # all routes by priority
python3 arion.py schema     # tracks → workspaces tree
python3 arion.py route "..." --json
```

The routing brain is [`core/router.py`](core/router.py); the keyword map is
[`config/routing.json`](config/routing.json). Edit keywords **only** in the
JSON (and add a matching test) — the folder READMEs are documentation.

## Test-Driven Development

Every feature lands RED → GREEN → REFACTOR. No structural logic is written
before a failing test pins its behaviour. See [`tasks.md`](tasks.md).

```bash
# Preferred
python3 -m pytest tests/ -q

# Zero-dependency fallback (no pytest required)
python3 -m unittest discover -s tests -v      # 17 tests, all green
```

## Deployment target

- **Sync branch:** `Robeul-Dev-Update`
- **Pipeline:** Tailnet IP mesh → SSH (`tl-host`) with Playwright verification

---

### Operator prerequisites (host machine)

- Windows Terminal or PowerShell opened as Administrator.
- Tailscale active (providing your Tailnet IP mesh).
- SSH access verified to your `tl-host` target server.
