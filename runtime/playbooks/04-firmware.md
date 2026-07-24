# Playbook: Agentic firmware

**Firmware** = a versioned agent package you sell or embed: roles, prompts, tools, policies, and I/O contract.

## Package shape (target)

```
firmware/<name>/
  manifest.yaml      # id, version, roles, tools, limits
  prompts/           # role prompts
  tools/             # tool defs or refs
  policies/          # allow/deny, PII, budgets
  tests/             # golden cases
  README.md          # customer-facing contract
```

## Rules

1. Semantic versioning (`MAJOR.MINOR.PATCH`).
2. Manifest declares every tool and model requirement.
3. Backward-compatible inputs when possible; document breaks in MAJOR.
4. Firmware must run on host workers without forking host code.
5. Include eval/golden tests before release.

## Implementation checklist

1. Spec `manifest.yaml` schema.
2. Loader in host/workers that pins version.
3. Sample firmware under `firmware/sample-assistant/`.
4. Release notes template.
5. Integration smoke test via host API.

## Acceptance criteria

- Load firmware by id+version and run a job end-to-end.
- Invalid/missing tools fail fast with clear errors.
