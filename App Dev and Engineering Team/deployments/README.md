# deployments/

System deployments via Tailnet SSH (`tl-host`) with Playwright integration.

**Owns:** deployment scripts, SSH/Tailnet provisioning, release pipelines,
and Playwright-driven post-deploy verification.

**Sync target:** branch `Robeul-Dev-Update` → `tl-host` over the Tailnet IP mesh.

**TDD contract:** deployment logic must have a failing verification test (e.g.
a dry-run/health-check assertion) before the deploy step is implemented.
