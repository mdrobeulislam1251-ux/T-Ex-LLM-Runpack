---
name: api-design
description: Use when designing, extending, reviewing, or debugging any HTTP API (REST or RPC) — route structure, request/response envelopes, status codes, auth token lifetimes, pagination, idempotency, rate limits, versioning — in any stack exposing HTTP endpoints (Next.js, FastAPI, Express, Go, or anything else).
---

# API Design

Portable contract rules for HTTP APIs. Stack-agnostic: probe the project first, then apply these defaults wherever the codebase hasn't already decided.

## Existing codebase wins

These defaults govern NEW APIs. In an established codebase, the incumbent envelope shape, naming style, pagination scheme, and error format win — a consistently "wrong" pattern beats a mixed one. Probe for incumbents before writing the first route:

POSIX:
```sh
find . -path '*/node_modules' -prune -o \( -name 'openapi.*' -o -name 'swagger.*' \) -print
grep -rn --include='*.ts' --include='*.js' --include='*.py' --include='*.go' \
  -E '"error"\s*:|nextCursor|next_cursor|requestId|request_id' . 2>/dev/null | grep -v node_modules | head -20
```

PowerShell:
```powershell
Get-ChildItem -Recurse -Include openapi.*,swagger.* -File | Where-Object FullName -NotMatch 'node_modules'
Get-ChildItem -Recurse -Include *.ts,*.js,*.py,*.go -File | Where-Object FullName -NotMatch 'node_modules' |
  Select-String -Pattern '"error"\s*:|nextCursor|next_cursor|requestId|request_id' | Select-Object -First 20
```

Found a convention? Follow it, and note in one line where it diverges from this file. Found nothing? These defaults apply in full.

## Detect the stack (probe, never assume)

Never assume framework, port, or validator. Read the project's own files:

POSIX:
```sh
ls package.json pyproject.toml requirements.txt go.mod Cargo.toml 2>/dev/null
grep -oE '"(next|express|fastify|hono|zod)"' package.json 2>/dev/null | sort -u
grep -iE 'fastapi|pydantic|flask|django' pyproject.toml requirements.txt 2>/dev/null
```

PowerShell:
```powershell
Get-ChildItem package.json,pyproject.toml,requirements.txt,go.mod,Cargo.toml -Name -ErrorAction SilentlyContinue
try { Select-String -Path package.json -Pattern '"(next|express|fastify|hono|zod)"' -ErrorAction Stop } catch {}
try { Select-String -Path pyproject.toml,requirements.txt -Pattern 'fastapi|pydantic|flask|django' -ErrorAction Stop } catch {}
```

The dev port comes from `.env`, the framework config, or the dev script in `package.json` — never from habit (3000/8000 are guesses, not facts).

## First principles

1. **APIs are contracts.** Design the shape before writing code.
2. **The API outlives the client.** Don't break consumers for a nicer internal structure.
3. **Predictability beats cleverness.** Same patterns everywhere > bespoke patterns per endpoint.

## Route structure (REST)

| HTTP | Path | Purpose |
|------|------|---------|
| `GET`    | `/resources`        | List (paginated, filterable) |
| `POST`   | `/resources`        | Create one |
| `GET`    | `/resources/{id}`   | Read one |
| `PATCH`  | `/resources/{id}`   | Update partial |
| `PUT`    | `/resources/{id}`   | Replace whole (rare, often avoid) |
| `DELETE` | `/resources/{id}`   | Soft or hard delete |
| `POST`   | `/resources/{id}/actions/<verb>` | Non-CRUD action |

- Resource names: plural, lowercase, kebab-case (`/email-accounts`, not `/EmailAccounts`)
- Nesting: max 1 level (`/campaigns/{id}/messages`). Deeper nesting = redesign.
- Query params for filtering and pagination; path params for identity.

## Request/response shapes

Standard JSON, one envelope:

```jsonc
// Success
{ "data": { /* resource or list */ }, "meta": { "page": 1, "total": 240 } }

// Error
{ "error": { "code": "VALIDATION_FAILED", "message": "email is required", "fields": { "email": "required" } } }
```

**Rules:**
- Every endpoint returns JSON (except binary downloads).
- `Content-Type: application/json` on writes.
- Timestamps: ISO 8601 UTC (`"2026-04-17T14:30:00Z"`) — NEVER Unix seconds in public APIs.
- IDs: strings (even if UUID). Numbers lose precision in JS for big ints.
- No nulls for missing fields — omit the field. Frontend checks `field in obj`.

## Status codes (use these, not random 200s)

| Code | When |
|------|------|
| 200 | OK, response has body |
| 201 | Created (include `Location: /resources/{id}` header) |
| 204 | No Content (DELETE success) |
| 400 | Validation error — body/param malformed |
| 401 | Not authenticated |
| 403 | Authenticated but forbidden |
| 404 | Resource doesn't exist |
| 409 | Conflict (duplicate, optimistic lock fail) |
| 422 | Semantic validation failed (was syntactically valid) |
| 429 | Rate limited (include `Retry-After` header) |
| 500 | Server bug |
| 502/503 | Upstream down / overloaded |

Never return 200 with `{"success": false}`. Use the right code.

## Auth

- **Bearer tokens** in `Authorization: Bearer <jwt>` for server-to-server and SPAs
- **HttpOnly cookies** with SameSite=Lax for browser sessions on your own domain
- **API keys** only for trusted first-party internal services. Name them (`X-Service-Key: ...`).
- Never put tokens in URL query strings (logged, cached, visible)

**CANONICAL TOKEN-LIFETIME RULE** — the single source of truth for T-Ex; no other skill may state a different number: access token TTL ≤ 15 minutes, refresh token TTL ≤ 7 days, rotate the refresh token on every refresh.

## Validation

Validate at the boundary. Reject early.

- **TypeScript/Node**: `zod` schemas, infer the types
- **Python/FastAPI**: `pydantic` models
- **Anywhere**: treat inputs as hostile; outputs go through the same schema

```ts
const CreateOrderSchema = z.object({
  contactId: z.string().uuid(),
  leadCount: z.number().int().min(1).max(100000),
  sourceUrl: z.string().url().startsWith('https://example.com'),
})

// In the handler:
const parsed = CreateOrderSchema.safeParse(await req.json())
if (!parsed.success) return Response.json({ error: { code: 'VALIDATION_FAILED', fields: parsed.error.flatten() } }, { status: 400 })
```

## Pagination

Prefer keyset over offset.

```
GET /contacts?limit=50&cursor=eyJpZCI6IjAxSE5...
```

Response includes `meta.nextCursor` (null when done). Offset pagination falls apart above ~10k rows — if the table can plausibly reach that, keyset from day one.

## Rate limiting

Think in two axes:
- **Per-user quotas** (API key / user id): e.g. 1000 req/hour
- **Per-endpoint shape** (e.g. `/search` vs `/healthz`): tighter limits on expensive endpoints

Use Redis (or the project's existing shared store) for distributed state. Return 429 + `Retry-After: <seconds>` header. Include `X-RateLimit-Remaining` in every response.

## Idempotency

For mutations, accept an optional `Idempotency-Key` header. Hash the request + key, cache the response for 24h, return the cached response on retry. Without this, clients retrying timeouts create duplicates.

## Versioning

- URL prefix: `/v1/...`. Easy, visible.
- Bump only for breaking changes. Adding fields is not breaking.
- Deprecate with `Deprecation:` and `Sunset:` response headers. Log usage.
- Keep old versions alive for at least 3 months past announce.

## Errors

Every error returns:
```json
{
  "error": {
    "code": "SNAKE_CASE_STRING",
    "message": "Human-readable English for logs",
    "requestId": "req_01HQ..."
  }
}
```

- **`code`** is programmatic — clients branch on it. Stable vocabulary.
- **`message`** is for humans — changes freely.
- **`requestId`** matches the value in server logs — essential for support.
- Never leak stack traces, SQL, or internal paths.

## Documentation

Write the OpenAPI/Swagger spec AS you design, not after:
- FastAPI auto-generates it from pydantic models
- Next.js: use `@asteasolutions/zod-to-openapi` or `next-rest`
- Express: `express-openapi-validator`

Commit the `openapi.yaml` to git. Diff it in PRs — schema drift = breaking change risk.

## Performance checklist

- Cache `GET` responses where safe: `Cache-Control: private, max-age=60` + `ETag`
- Return partial responses for expensive endpoints: `?fields=id,email,verified`
- Batch when iterating: `POST /contacts/bulk` accepting 100+ items rather than 100 single calls
- Background long work: return `202 Accepted` with a polling URL or webhook

## Anti-patterns to reject

- `/getUser`, `/createUser`, `/deleteUser` — not REST. Use `/users/{id}`.
- Verbs in URLs outside the `/actions/<verb>` escape hatch.
- 200 OK with error body.
- Returning HTML from JSON APIs on error.
- Mixing data and metadata at the top level: `{"id": 1, "data": [...]}` — nest one level.
- Breaking without a version bump.
- Undocumented endpoints in production.
- Secret fields in responses (`password_hash`, internal `_id`).

## Testing & done-gate

- Contract tests: call each endpoint, assert shape matches schema. Cheap, catches 80% of bugs.
- Golden-file tests for error responses: assert the exact error envelope.
- Integration tests: real DB, real HTTP. Slow but high-value for payment/auth flows.
- Load tests: `k6` or `hey`. Run at 1×, 10×, 100× expected peak before shipping.

Live verification (port taken from the project's own config, not assumed):

POSIX:
```sh
curl -s -o /dev/null -w '%{http_code}\n' "http://localhost:${PORT}/v1/resources"
```

PowerShell (use `curl.exe` — bare `curl` aliases Invoke-WebRequest in Windows PowerShell):
```powershell
curl.exe -s -o NUL -w "%{http_code}`n" "http://localhost:$env:PORT/v1/resources"
```

DONE-GATE — an API change is done only when ALL hold; anything less is reported as "written, not verified":
1. Every new/changed endpoint was hit with a real request and returned the documented status code (show the actual code, as above).
2. A malformed body was actually sent and came back `400` with `code: "VALIDATION_FAILED"` in the envelope (show the response).
3. The OpenAPI spec change is in the same commit as the route change — spec diff without route diff or vice versa = FAIL.
4. Error responses match the envelope in this file (or the codebase's incumbent envelope, per "Existing codebase wins") byte-for-byte in a golden test.
