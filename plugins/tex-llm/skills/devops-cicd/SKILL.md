---
name: devops-cicd
description: Use for CI/CD pipelines, GitHub Actions, build/test/deploy automation, environment promotion, release versioning, deploy strategies (rolling, blue-green, canary), rollback doctrine, and CI secrets — the platform in use is probed from repo files, never assumed.
---

# DevOps & CI/CD

The pipeline is a gate, not a ritual: it must be able to fail, promote one artifact through environments, and roll back in minutes.

## Probe

Which CI already exists? Look before proposing: `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/`, `azure-pipelines.yml`. Extend what's there in its own style. `gh auth status` tells you if the GitHub CLI is usable for runs/logs (`gh run list`, `gh run view --log-failed`).

## Pipeline doctrine

- Stage order = cheapest first, fail fast: lint → typecheck → unit → build → integration/e2e → deploy.
- Numeric: PR feedback **> 10 min** = split, parallelize, or cache. Cache keys come from the **lockfile hash**, never the branch name.
- **Build once, promote the same artifact** dev → staging → prod. Config is injected per environment at deploy. Rebuilding per env ships an artifact prod has never tested.
- Every CI step must run locally too (`package.json` scripts / Makefile) — YAML only orchestrates; logic lives in scripts you can debug.

## GitHub Actions — the minimal correct workflow

```yaml
name: ci
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read            # least privilege by default; widen per job only when needed
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm        # caches the npm store keyed on the lockfile
      - run: npm ci
      - run: npm run lint
      - run: npm test -- --ci
```

### Actions errors → fixes

| Verbatim output | Fix |
|---|---|
| `Resource not accessible by integration` | `GITHUB_TOKEN` lacks a permission for what the step does — add it to the `permissions:` block (e.g. `pull-requests: write` to comment) |
| `refusing to allow an OAuth App to create or update workflow` | The pushing token lacks the `workflow` scope — re-auth with it or push workflow changes with proper credentials |
| Deps reinstall despite cache hit | Cache stored the wrong path — prefer `setup-node`'s `cache:` over hand-rolled `actions/cache` on `node_modules` |
| `fatal: could not read Username for 'https://github.com'` | Job touches a private repo/submodule — `GITHUB_TOKEN` is repo-scoped; use a deploy key or fine-grained PAT secret |
| Secrets empty on a PR run | Fork PRs get no secrets by design — gate deploy/integration jobs on `push` events or protected environments |

## Secrets in CI

- Platform secret store only. Never `echo` one; masking breaks the moment you interpolate it into a URL that a failing command prints.
- Prefer **OIDC federation** to cloud providers (e.g. `aws-actions/configure-aws-credentials` with `role-to-assume`) over long-lived keys stored as secrets.
- Numeric: any long-lived CI credential rotates **≤ 90 days**; keep a written map of which workflow reads which secret.

## Versioning & releases

- Tag = immutable release pointer, `vMAJOR.MINOR.PATCH`. The artifact also carries the commit: `myapp:1.4.2` AND `myapp:sha-<12>`.
- Conventional commits (`feat:` / `fix:` / `BREAKING CHANGE:`) make changelog + version bump mechanical.
- A release is produced BY the pipeline (tag → build → publish → changelog). A binary built on a laptop is not a release.

## Deploy strategies

| Strategy | When | Mechanics | Rollback |
|---|---|---|---|
| Rolling | Default for stateless services | Replace instances gradually behind LB health checks | Redeploy previous artifact |
| Blue-green | Need instant, total cutover | Two full stacks; flip the router | Flip back — seconds |
| Canary | Risky change, validate on real traffic | 5–10% of traffic to the new version, watch 15–30 min, then promote | Route 100% back |

Health-gate before full promotion, with numbers: error rate **< 1%** and p95 latency within **20%** of baseline — otherwise auto-abort. A canary nobody watches is just a slow rollout.

## Rollback doctrine

- Rollback = **redeploy the previous artifact**. Not `git revert` + rebuild under incident pressure — that's slow and produces a never-tested binary.
- Keep N-1 deployable at all times. Numeric: rollback decision within **5 minutes** of a bad signal; argue root cause in the postmortem, not during the incident.
- Database changes are DECOUPLED from deploys via expand/contract (`postgres-patterns`) so code N-1 and N both run against the live schema — that is the thing that makes rollback safe at all.
- After a rollback: deploys freeze until the root cause has a name.

## Branch & PR discipline

- Protected default branch: required status checks + review, no direct pushes — including yours.
- Short-lived branches; squash-merge keeps history linear so every release tag maps to one commit.

## Done-gates

- **Pipeline done** = green on a real PR **and** a deliberately broken test turns it red. A gate that cannot fail is not a gate — prove it once.
- **Deploy done** = new version answers its health endpoint in the target environment AND one key user flow probed after deploy (`verification-gates`). "Workflow green" is compiled-not-verified.
- **Rollback done** = exercised once for real in staging (deploy vN, roll back to vN-1, health-check). An untested rollback plan is a hope, not a plan.
- **Secrets done** = zero secrets in repo history or committed config; CI logs show masked values only.
