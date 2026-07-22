---
name: project-bootstrap
description: Use when handed a new or unfamiliar project, when the user says "set up", "start development", or sends project docs to build, and on any credential-shaped failure (401, auth failed, missing env var) — inventories the stack, live-verifies every backend credential, fixes what's fixable, asks at most ONE batched question, then starts building.
---

# Project Bootstrap

One call sets you up. The user never feeds you credentials one question at a time — you find them, test them, and report a ledger. This skill exists because clarifying-question storms and credential fumbling are the fastest way an agent burns user trust.

**The contract: probe everything → fix what you can → ask ONE batched question (or none) → build.**

## Step 0 — Recon

Run the light recon from `environment-recon` first (OS, shell, cwd, stack markers, package manager actually in use). This skill takes over for the backend surface.

## Step 1 — Inventory the secret surface

Find every file that can hold config or credentials — file NAMES only, never print contents:

```powershell
# PowerShell
Get-ChildItem -Recurse -Depth 3 -Force -File -Include '.env*','*.env','docker-compose*.yml','docker-compose*.yaml','appsettings*.json','config.toml','wrangler.toml','serverless.yml','.npmrc' -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -notmatch 'node_modules|\\\.git\\' } | Select-Object -ExpandProperty FullName
```
```sh
# POSIX
find . -maxdepth 3 \( -path ./node_modules -o -path ./.git \) -prune -o -type f \
  \( -name '.env*' -o -name '*.env' -o -name 'docker-compose*.y*ml' -o -name 'appsettings*.json' \
     -o -name 'config.toml' -o -name 'wrangler.toml' -o -name 'serverless.yml' -o -name '.npmrc' \) -print
```

**Gitignore gate — before anything else:** if a real `.env` exists and git would track it, fix that NOW. A committed secret is the one mistake you can't fully undo.

```sh
# POSIX
git check-ignore -q .env && echo COVERED || echo 'NOT COVERED — add .env* to .gitignore before any other work'
```
```powershell
# PowerShell
git check-ignore -q .env; if ($LASTEXITCODE -eq 0) { 'COVERED' } else { 'NOT COVERED — add .env* to .gitignore before any other work' }
```

## Step 2 — Extract what the code actually needs

Three lists: **REQUIRED** (vars the code reads), **PRESENT** (vars defined in env files), **MISSING** = REQUIRED − PRESENT.

```sh
# POSIX — REQUIRED: vars the code reads
grep -rhoE 'process\.env\.[A-Z0-9_]+|import\.meta\.env\.[A-Z0-9_]+' . \
  --include='*.js' --include='*.ts' --include='*.tsx' --include='*.jsx' --include='*.mjs' \
  --exclude-dir=node_modules 2>/dev/null | grep -oE '[A-Z][A-Z0-9_]{2,}' | sort -u
# Python projects: grep for os\.environ and os\.getenv the same way.
```
```powershell
# PowerShell — REQUIRED
Get-ChildItem -Recurse -Include *.js,*.ts,*.tsx,*.jsx,*.mjs -File |
  Where-Object { $_.FullName -notmatch 'node_modules' } |
  Select-String -Pattern 'process\.env\.([A-Z0-9_]+)|import\.meta\.env\.([A-Z0-9_]+)' -AllMatches |
  ForEach-Object { $_.Matches | ForEach-Object { $_.Groups[1].Value + $_.Groups[2].Value } } | Sort-Object -Unique
```
```sh
# POSIX — PRESENT: names only, values never printed
grep -hoE '^[A-Z][A-Z0-9_]*=' .env .env.* 2>/dev/null | tr -d '=' | sort -u
```
```powershell
# PowerShell — PRESENT
Get-Content .env,.env.* -ErrorAction SilentlyContinue |
  ForEach-Object { if ($_ -match '^([A-Z][A-Z0-9_]*)=') { $Matches[1] } } | Sort-Object -Unique
```

`.env.example` is the project's own declaration of REQUIRED — when it disagrees with your grep, trust the example file and investigate the difference.

## Step 3 — Live-verify every credential

Rules: probes are **READ-ONLY** (health endpoints, `select 1`, ping — never a write). Timeout every probe at ~10s. Never echo a secret — mask rule in Step 4. In PowerShell use `curl.exe` — bare `curl` aliases `Invoke-WebRequest` in PS 5.1.

| Var pattern | Probe (POSIX form) | Healthy output |
|---|---|---|
| `DATABASE_URL`, `PG*` | `psql "$DATABASE_URL" -tAc 'select 1'` | `1` — deeper triage in `postgres-patterns` |
| `SUPABASE_URL` + keys | `curl -sS -o /dev/null -w '%{http_code}' "$SUPABASE_URL/auth/v1/health" -H "apikey: $SUPABASE_ANON_KEY"` | `200` — key roles in `supabase-platform` |
| `REDIS_URL` | `redis-cli -u "$REDIS_URL" ping` | `PONG` |
| `MONGODB_URI` | `mongosh "$MONGODB_URI" --quiet --eval 'db.runCommand({ping:1}).ok'` | `1` |
| `ELASTICSEARCH_*` / `OPENSEARCH_*` | `curl -sS -u "$ES_USER:$ES_PASS" "$ES_URL/_cluster/health?filter_path=status"` | `green` or `yellow` — see `elasticsearch-opensearch` |
| `CLICKHOUSE_*` | `curl -sS "$CLICKHOUSE_URL/ping"` | `Ok.` |
| `AWS_*` / `S3_*` | `aws s3api head-bucket --bucket "$S3_BUCKET"` | exit 0 |
| `SMTP_*` | `nc -vz -w 5 "$SMTP_HOST" "${SMTP_PORT:-587}"` (PS: `Test-NetConnection $env:SMTP_HOST -Port 587`) | reachable — auth is proven only by a real send: mark UNTESTED, not OK |
| `STRIPE_SECRET_KEY` | `curl -sS -o /dev/null -w '%{http_code}' https://api.stripe.com/v1/balance -u "$STRIPE_SECRET_KEY:"` | `200` |
| any `*_API_KEY` with a documented base URL | the cheapest authenticated GET that vendor documents | `200` |

### Probe outcome → meaning

| Outcome | Meaning → action |
|---|---|
| HTTP `401` | Key wrong, expired, or from a different project — mark INVALID; goes in the batched ask |
| HTTP `403` | Key valid but lacks scope/role (or RLS denies) — usually fixable by using the right key TIER, not a new secret |
| HTTP `404` on a health path | Base URL wrong (typo'd project ref or host) — fix the URL, not the key |
| `Could not resolve host` / `ENOTFOUND` | Hostname typo, DNS, or VPN — route to `network-diagnosis` |
| `Connection refused` | Right host, nothing listening — service down or wrong port; check compose/container state first (`docker-operations`) |
| Hard timeout | Firewall / IP-allowlist — check the vendor dashboard allowlist before blaming the key |
| JWT probe shows `exp` in the past | Expired token. Decode payload: `node -e "const p=process.env.KEY.split('.')[1];console.log(JSON.parse(Buffer.from(p,'base64url').toString()))"` |

## Step 4 — The credential ledger

Report exactly ONE table, then move on:

```
VAR                    SOURCE       PROBE                      STATUS
DATABASE_URL           .env         select 1 → 1               OK
SUPABASE_SERVICE_KEY   .env         auth/v1/health → 401       INVALID
SMTP_PASS              .env         port 587 reachable         UNTESTED (proven on first send)
OPENAI_API_KEY         (nowhere)    —                          MISSING
```

**Mask rule:** if a value must be referenced at all, show the first 4 characters + length — `sk-p… (51 chars)`. Full secret values never appear in chat, logs, commit messages, or error reports.

## Step 5 — Fix without asking

Fix yourself, then note it in the ledger:

- `.env` absent but `.env.example` present → copy it; fill every NON-secret (URLs, ports, flags) from compose/config/docs; secret values stay empty and go to Step 6.
- Host says `localhost` but the service runs in compose → service name inside the network, `localhost:<published port>` from the host.
- Port drift (env says 5432, compose publishes 5433) → align env to reality, never reality to env.
- Managed Postgres refusing plain connections → add `sslmode=require` (exact error strings in `postgres-patterns`).
- Key tier in the wrong place (service-role key in browser code, anon key in a server job) → swap the usage, not the secrets.

NEVER invent or guess: actual secret values, OAuth client secrets, third-party dashboard state, anything that spends money.

## Step 6 — The one question

Numeric gate: **≤ 1 credential question per bootstrap**, asked only after every probe has run. Format:

> Everything else is verified; the base build is ready to start. I need exactly 2 values I can't derive:
> 1. `OPENAI_API_KEY` — missing everywhere (code reads it in the AI client module)
> 2. `SUPABASE_SERVICE_KEY` — present but the API answers 401 (expired or wrong project)
>
> Paste them into `.env` (not into chat) and say "go".

Forbidden in the ask: anything sitting in a file you didn't read, anything a probe can answer, option menus the repo already decides.

## Step 7 — Build

Bootstrap is setup, not the deliverable. Ledger green (or the one ask answered) → straight into the build (`fullstack-delivery`), starting from the doc the user sent. Doc-driven loop: build the full base → prove it runs (`verification-gates`) → report → stop. The next doc the user sends starts the next cycle — never redesign what an earlier cycle already verified.

## Anti-patterns — each one burns user trust

- Asking for a credential that sits in a file you never opened.
- Asking questions one at a time as failures surface — collect, then batch.
- Echoing a secret value into chat or logs "to confirm it's right".
- Probing with writes (INSERT test rows, POST test orders). Read-only means read-only.
- Marking a var OK because it EXISTS — existence ≠ validity; only a live probe upgrades status.
- Blocking the whole build on one missing OPTIONAL var — feature-flag it, note it, proceed.

## Done-gates

- **Bootstrap done** = every REQUIRED var is OK, FIXED, named in the single batched ask, or explicitly parked as optional. Zero vars left silently UNTESTED.
- Never report "environment set up" while any ledger probe failed — the ledger IS the report.
