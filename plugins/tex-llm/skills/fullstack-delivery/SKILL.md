---
name: fullstack-delivery
description: Use when a task changes both client and server of an existing codebase — a new feature slice, a new endpoint plus its UI, or any change that crosses the frontend/backend boundary.
---

# Fullstack Delivery — One Feature Slice Across the Boundary

Governs how a feature ships across frontend + backend in ANY existing repo. The stack is whatever the repo says it is — every fact below is probed from the project, never assumed. Order is fixed: discover conventions → contract → server → client → wire → drive the running app.

## Scope Rules (before anything)

- **Edit in place.** No `_v2`, `.bak`, `-copy`, `-new` files, ever. Version control is the history. If the repo has no git, say so in one line and still edit in place.
- **Exact ask only.** User pastes code and says "fix X" → fix X. Do not refactor the file, rename variables, or reformat untouched lines. Side-issues get one reported line, zero unrequested edits.
- **Size the solution to the ask.** A task expressible in under ~50 lines with no persistence = one script file. No project generator, no build step for a static HTML page, no framework added to a working non-framework project without asking.
- **Match existing deps.** Check the manifest (`package.json`, `pyproject.toml`, `go.mod`, `Gemfile`, `composer.json`, `*.csproj`) before importing anything. A new dependency needs one line justifying why the existing ones can't do it. Never add a second tool for a job the repo already solves — no second HTTP client, second validator, second CSS approach.
- **Small files.** One component/handler per file. A file crossing ~300 lines gets split — but only when the ask already touches it, never as a drive-by.
- **Secrets and endpoints via env.** Read config the way the repo already does (probe #9). Never hardcode a URL, port, or key that an existing env/config file owns; never print or commit a secret value.
- **Tests:** write them if the repo has a test suite and the feature is production-bound; don't invent a test framework for a repo that has none unless asked.

## 1. Convention Discovery (run BEFORE writing any code)

Probes use `rg` (ripgrep — identical syntax on Windows and POSIX). If rg is absent:
POSIX `grep -rEn "<pattern>" src/` · PowerShell `Get-ChildItem -Recurse src | Select-String -Pattern "<pattern>"`.

Probes are written POSIX-first; each one that differs has a `# PowerShell:` line under it. The three mechanical swaps: `| head -N` → `| Select-Object -First N` · `2>/dev/null` → `2>$null` · multi-path `ls a b c` → `Get-ChildItem a,b,c -ErrorAction SilentlyContinue`.

```bash
# 1. Stack + package manager (lockfile decides, not preference):
ls package.json pnpm-lock.yaml yarn.lock package-lock.json bun.lockb pyproject.toml uv.lock requirements*.txt go.mod Cargo.toml 2>/dev/null
# PowerShell: Get-ChildItem package.json,pnpm-lock.yaml,yarn.lock,package-lock.json,bun.lockb,pyproject.toml,uv.lock,go.mod -ErrorAction SilentlyContinue

# 2. How the app runs in dev (read the port from here or from startup output — never guess it):
rg '"(dev|start|serve)"' package.json ; ls Makefile docker-compose*.yml Procfile 2>/dev/null
# PowerShell: rg '"(dev|start|serve)"' package.json ; Get-ChildItem Makefile,docker-compose*.yml,Procfile -ErrorAction SilentlyContinue

# 3. File naming + layout — list an existing feature's folder and copy its shape:
rg --files src app lib | head -40
# PowerShell: rg --files src app lib 2>$null | Select-Object -First 40

# 4. Client data fetching — which ONE pattern does this repo use?
rg -l "useQuery|useSWR|createApi|useFetch|axios\.|fetch\(" --glob '!node_modules' | head -10
# PowerShell: rg -l "useQuery|useSWR|createApi|useFetch|axios\.|fetch\(" --glob '!node_modules' | Select-Object -First 10

# 5. Server error shape — find how an existing handler returns a 4xx:
rg -n "status\(4|HTTPException|abort\(4|BadRequest|problem\+json|res\.status" | head -10
# PowerShell: rg -n "status\(4|HTTPException|abort\(4|BadRequest|problem\+json|res\.status" | Select-Object -First 10

# 6. Input validation — which validator is canon?
rg -l "zod|yup|joi|valibot|class-validator|pydantic|marshmallow|validator\." --glob '!node_modules' | head -5
# PowerShell: rg -l "zod|yup|joi|valibot|class-validator|pydantic|marshmallow|validator\." --glob '!node_modules' | Select-Object -First 5

# 7. Boundary types — does codegen already exist? (this decides the type-sync rule below)
rg -n "openapi|graphql-codegen|orval|swagger|prisma generate|trpc|protoc|NSwag" package.json Makefile pyproject.toml 2>/dev/null
# PowerShell: rg -n "openapi|graphql-codegen|orval|swagger|prisma generate|trpc|protoc|NSwag" package.json Makefile pyproject.toml 2>$null

# 8. Auth transport — cookie or bearer header? (decides which failure rows below can bite)
rg -n -l "credentials.*include|withCredentials|Authorization.*Bearer|Set-Cookie" --glob '!node_modules' | head -5
# PowerShell: rg -n -l "credentials.*include|withCredentials|Authorization.*Bearer|Set-Cookie" --glob '!node_modules' | Select-Object -First 5

# 9. Config/env handling — where do URLs and secrets come from in THIS repo?
ls .env.example .env.sample .env.template config/ 2>/dev/null
# PowerShell: Get-ChildItem .env.example,.env.sample,.env.template,config -ErrorAction SilentlyContinue
rg -n "process\.env\.|os\.environ|os\.Getenv|import\.meta\.env|Deno\.env" --glob '!node_modules' | head -10
# PowerShell: rg -n "process\.env\.|os\.environ|os\.Getenv|import\.meta\.env|Deno\.env" --glob '!node_modules' | Select-Object -First 10

# 10. Repo's own quality gates — what must pass before "done"? Run these, add none:
rg '"(typecheck|lint|test|check|e2e)"' package.json ; rg -n "\[tool\.(ruff|mypy|pytest)" pyproject.toml 2>/dev/null
# PowerShell: rg '"(typecheck|lint|test|check|e2e)"' package.json ; rg -n "\[tool\.(ruff|mypy|pytest)" pyproject.toml 2>$null
```

**Decision rules:**
- 3 existing examples agreeing = the convention. Follow it even if you'd choose differently.
- Examples conflict → follow the most recently modified one; note the conflict in one line.
- Zero examples (truly new territory) → pick the stack's mainstream default and say which you picked.
- Probe #7 hit = codegen path in the type-sync rule; no hit = shared-types path. Decide now, not mid-slice.

## 2. The Feature-Slice Order

Build in this order. Each step is verified before the next starts.

**1. Contract first.** ONE contract both sides code against — the single source of truth for URL, method, request shape, response shape, AND error shape. Write it in the medium probe #7 found: OpenAPI spec, GraphQL schema, tRPC router, protobuf, or a shared types module. The frontend calls the backend only through this contract — never against a remembered or imagined API.

**2. Schema/migration** (only if data changes). Use the repo's existing migration tool:

```bash
rg -l "migrations|alembic|flyway|knex|prisma/schema|migrate" --glob '!node_modules' | head -5
```
```powershell
rg -l "migrations|alembic|flyway|knex|prisma/schema|migrate" --glob '!node_modules' | Select-Object -First 5
```

Never raw DDL against a live DB outside the migration flow; never edit an already-applied migration file — add a new one.

**3. Server.** Implement the endpoint against the contract. Verify with a direct HTTP call BEFORE writing any client code:

```bash
# POSIX — and Windows too if you call the real binary:
# (bare `curl` in Windows PowerShell 5.1 is an alias for Invoke-WebRequest; always type curl.exe there)
curl -sS -i -X POST "http://localhost:<port-from-probe-2>/<route>" \
  -H "Content-Type: application/json" -d '{"field":"value"}'
```
```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:<port>/<route>" `
  -ContentType "application/json" -Body '{"field":"value"}'
```

Then send one INVALID payload the same way and capture the error status + body — that observed shape is what the client will parse in step 4.

**4. Client.** Fetch and parse using the same contract types, following probe #4's one pattern. Handle the error shape you actually saw in step 3, not an imagined `{error: string}`.

**5. Wire + drive.** Connect UI to the call, start the app with probe #2's command, and drive the flow (Done-Gate, section 4).

### Type-sync rule (the boundary invariant)

- Repo HAS codegen (probe #7 hit) → change the source of truth, rerun the generator, commit its output per repo convention. Never hand-edit generated files.
- Repo has NO codegen → one shared types module imported by both sides (same-language stacks); for split-language stacks the contract file itself is the reference and each side's types carry a comment pointing at it. Never maintain two hand-written copies of the same shape.
- **The drift failure mode:** both sides compile green while prod breaks. Server renames `user_name` → `username`; the client's stale copy still typechecks because it is a copy; the break surfaces as `undefined` in the UI at runtime, not as a build error. After any contract change:

```bash
rg "old_field_name" --glob '!node_modules'   # must return ZERO hits (includes tests and mocks) before moving on
```

## 3. Integration Failure Playbook

Classic cross-boundary failures, with the message you actually see.

1. Browser console:
   `Access to fetch at 'http://localhost:<api-port>/...' from origin 'http://localhost:<ui-port>' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.`
   — while the same URL works in curl.
   Cause: UI dev server and API on different ports; curl bypasses the browser's origin check, so "works in curl, fails in browser" is the CORS signature.
   Fix: prefer a dev proxy so the browser sees one origin — Vite `server.proxy`, CRA `"proxy"`, Next.js `rewrites()`, webpack `devServer.proxy`. If you must set headers instead: echo the exact dev origin (not `*`) and answer the `OPTIONS` preflight with the allowed methods/headers.

2. Login returns 200 with a `Set-Cookie` header, but the very next request is 401; DevTools shows the cookie was never attached.
   Cause: cross-origin `fetch` omits cookies by default, and browsers drop cross-site cookies lacking `SameSite=None; Secure`.
   Fix — ALL three, or it silently fails: client `credentials: 'include'` (axios: `withCredentials: true`); server `Access-Control-Allow-Credentials: true` plus the exact origin (`*` is rejected when credentials are on); cookie flags `SameSite=None; Secure`. On plain-http localhost `Secure` cannot be satisfied — route through the same-origin dev proxy from entry 1 instead, and `SameSite=Lax` just works.

3. UI shows "undefined" or a blank toast on invalid input; the network tab shows a 422 with a real body such as:
   `{"detail":[{"loc":["body","email"],"msg":"field required","type":"value_error.missing"}]}`
   Cause: client error parser expects a different shape than the server validator emits — FastAPI `detail[]`, Zod `issues[]`, Rails `errors{}`, express-validator `errors[]` all differ.
   Fix: the error shape is PART of the contract (slice step 1). Parse the shape captured in step 3's invalid-payload call and define the error type next to the response type.

4. A field renamed on the server; client still compiles; UI renders `undefined` where the value used to be.
   Cause: stale hand-copied client types — the drift failure mode above.
   Fix: rerun codegen or update the shared type, then run the zero-hit grep on the old name.

5. Server logs the received body as a quoted string — `"{\"a\":1}"` — or the validator answers `Expected object, received string`.
   Cause: body serialized twice: `JSON.stringify` applied to already-stringified data, or an HTTP wrapper that serializes objects was handed a pre-stringified string.
   Fix: stringify exactly once, at the transport layer only. Axios/got/ky and most wrappers serialize objects themselves — pass the object. Trace the call chain and delete the extra `JSON.stringify`.

6. Server receives `{}` or all-`None`/`null` fields although DevTools shows the payload leaving the browser.
   Cause: missing or wrong `Content-Type` (raw `fetch` with a string body defaults to `text/plain`), so the framework's JSON body parser never ran.
   Fix: set `Content-Type: application/json` on the request; confirm JSON body parsing is enabled for that route on the server.

## 4. Done-Gate

A slice is done only when ALL pass. Unit tests alone NEVER satisfy this gate; exit-0 is "compiled, not run-verified".

1. **Server proof:** the new route answered a real HTTP call (step-3 commands) — success case AND one invalid-input case, actual status + body quoted in the report.
2. **Driven flow:** the running app was actually driven end-to-end — page loaded, action performed, result observed. Use the repo's e2e runner if one exists:

   ```bash
   rg -n "playwright|cypress|@testing-library|webdriver" package.json 2>/dev/null
   ```
   ```powershell
   rg -n "playwright|cypress|@testing-library|webdriver" package.json 2>$null
   ```

   Otherwise drive with Playwright directly — minimal throwaway drive script (needs `npx playwright install chromium` once):

   ```js
   // drive.mjs — run: node drive.mjs   (delete after verifying; it is proof, not product)
   import { chromium } from "playwright";
   const browser = await chromium.launch();
   const page = await browser.newPage();
   page.on("pageerror", e => { console.error("PAGE ERROR:", e); process.exitCode = 1; });
   await page.goto("http://localhost:<port-from-probe-2>/<feature-page>");
   await page.fill("<input-selector>", "test value");
   await page.click("<submit-selector>");
   await page.waitForSelector("<selector-proving-the-new-state>", { timeout: 5000 });
   console.log("DRIVEN OK:", await page.textContent("<selector-proving-the-new-state>"));
   await browser.close();
   ```

   No browser automation available → drive manually and state the observed outcome: "submitted the form, new row rendered in the list".
3. **Round-trip:** data created through the UI is observable on the far side of the boundary — re-fetched via the API or queried in the store. Optimistic UI state alone does not count.
4. **Error path driven:** one invalid input entered through the UI renders a real message — not "undefined", not an unhandled promise rejection in the console.
5. **Repo's own checks:** whatever the manifest defines (`typecheck`, `lint`, `test`) runs clean. Run only what exists — add none.
6. **Drift check:** if the contract changed, the old-name grep from the type-sync rule returned zero hits.

Report format: lead with the outcome ("Slice shipped and driven: created X through the UI, re-read it via GET /<route>"), then only the detail that changes the user's next action. Anything not verified is labeled `[NOT verified]`.
