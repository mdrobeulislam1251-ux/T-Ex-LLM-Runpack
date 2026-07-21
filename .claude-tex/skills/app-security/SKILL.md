---
name: app-security
description: Use for application security work — auth (sessions, JWT, OAuth), authorization/IDOR, input validation, security headers, secrets handling, dependency audits, file uploads, rate limiting, and native/mobile secure storage — with verification commands to prove each control actually works.
---

# Application Security

Security is controls you can PROBE, not vibes. Every control here ends in a check you run. Scope: the app layer — server hardening lives in `server-ops-safety`, credential bootstrap in `project-bootstrap`.

## The non-negotiables (any stack)

| Threat | Control — no exceptions |
|---|---|
| SQL injection | Parameterized queries / ORM bindings ONLY. String-built SQL with user input fails review even "just for search". |
| XSS | Framework auto-escaping stays ON; no `dangerouslySetInnerHTML`/`innerHTML` with user data (sanitize server-side if unavoidable); CSP header as backstop. |
| CSRF | SameSite cookies (`Lax` minimum) + CSRF token on state-changing browser form/cookie flows. Pure Bearer-token APIs are exempt — cookies are not. |
| IDOR / broken authz | EVERY endpoint checks object OWNERSHIP server-side (`WHERE id = ? AND user_id = ?`), not just "is logged in". Client-side checks are UI, not security. |
| Secrets in code | Env/secret store only. Pre-commit scan (below). A leaked secret is ROTATED, never just deleted from the file — git history remembers. |
| Mass assignment | Explicit allowlist of writable fields per endpoint (`role`, `is_admin`, `credits` are the classic smuggled fields). |

## Authentication

- **Passwords**: argon2id (preferred) or bcrypt with cost ≥ 12. Never MD5/SHA-x, never homebrew. Max-length cap ≥ 64 chars, no forced rotation, check against breached-password lists on set.
- **Sessions (server-rendered/SPA + API on same site)**: httpOnly + Secure + SameSite cookies; new session ID on login (fixation); absolute + idle timeouts.
- **JWT (when you actually need statelessness)**: access token TTL **≤ 15 min**; refresh token rotated on every use, revocable server-side; algorithm pinned (`HS256`/`RS256` explicitly — never accept `alg: none` or "whatever the header says"); validate `iss`, `aud`, `exp` every request.
- **Token storage in browsers**: httpOnly cookie. localStorage/sessionStorage for auth tokens fails review — any XSS becomes full account takeover.
- **OAuth**: exact-match redirect URI allowlist; `state` parameter verified; PKCE for public clients.
- **Login endpoints**: rate-limited (below) + constant-response-time on user-not-found vs wrong-password (no user enumeration; same rule for password-reset responses).

## Authorization

- Deny by default: routes are protected unless explicitly public — an unlisted new route must come out locked.
- Roles checked server-side per request, from the session/token — never from a client-supplied field.
- **The two-user probe (run it, every review):** create user A and user B; as B, request A's object by ID on every resource type:

```sh
curl -sS -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $TOKEN_B" "$APP_URL/api/orders/$ORDER_ID_OF_A"
# 403/404 = pass. 200 = IDOR — stop the release.
```

## Input validation & uploads

- Validate at the boundary with a schema (zod/joi/pydantic/DTO validation): type, length, range, format — allowlist, not blocklist. Reject, don't "clean".
- Path traversal: user input never concatenated into filesystem paths; resolve + verify the result stays under the intended root.
- File uploads: size cap enforced server-side; type checked by CONTENT (magic bytes), not extension or Content-Type header; stored outside the webroot / in object storage under a server-generated name; never executable; images re-encoded.
- Server-side request forgery: any user-supplied URL your server fetches gets an allowlist + private-IP/metadata-endpoint block (169.254.169.254 is the classic theft target).

## Security headers (copy, then verify)

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'; frame-ancestors 'none'  (tighten per app; start report-only)
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

Verify what production ACTUALLY sends (PS 5.1: `curl.exe`):

```sh
curl -sSI "$APP_URL" | grep -iE 'strict-transport|content-security|x-content-type|referrer-policy|permissions-policy'
```

- **CORS**: explicit origin allowlist. `Access-Control-Allow-Origin: *` combined with credentials fails review; reflecting the request's Origin unchecked is the same bug in disguise.
- Errors in prod: generic message + logged reference ID. Stack traces, ORM errors, and framework debug pages OFF — verify by forcing a 500 and reading what the client sees.

## Rate limiting & abuse

| Endpoint class | Starting limit |
|---|---|
| Login / OTP / password reset | 5/min per account AND per IP, exponential backoff |
| Signup, contact/email-sending forms | 3/min per IP + CAPTCHA after abuse |
| General authenticated API | 100–600/min per user (tune on real traffic) |
| Expensive endpoints (search, export, AI calls) | separate low bucket, queue overflow |

429 with `Retry-After`. No rate limit on auth endpoints = credential-stuffing target.

## Secrets & dependencies

```sh
# secrets sweep before every push (dedicated tool if available, grep as minimum)
gitleaks detect --source . 2>/dev/null || grep -rnE "(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}" --include='*.{js,ts,py,cs,kt,swift,json,yml,yaml,env}' --exclude-dir={node_modules,.git,dist} .

# dependency audit (run the one matching the lockfile)
npm audit --omit=dev        # or: pip-audit / dotnet list package --vulnerable / cargo audit
```

- Lockfiles committed; CI fails on **critical/high** vulns (triaged exceptions documented with an expiry date).
- Leak response: rotate the secret at the provider FIRST, then clean the repo. History rewrite without rotation is theater.

## Native & mobile apps

- Secrets on device: Keychain (iOS/macOS) / Keystore-backed EncryptedSharedPreferences (Android) / DPAPI (Windows) — never plaintext prefs, SQLite, or files.
- Anything shipped IN the binary is public — API keys in app code are extractable in minutes; real secrets stay server-side behind your API.
- TLS always; certificate pinning only with a rotation plan (pinning without one bricks your app on cert renewal).
- Sensitive screens: flag against screenshots/app-switcher exposure where the platform supports it.

## Done-gates

- **Auth done** = cookie flags verified in the browser/`curl -I`, token TTLs proven (expired token actually rejected), login rate-limit fires in a test.
- **Authz done** = the two-user probe ran across every resource type — passing code review is not passing the probe.
- **Headers done** = the curl sweep shows every header in PRODUCTION config, not localhost.
- **Secrets done** = sweep clean AND `.env*` gitignored AND no secret ever printed in logs/CI output.
- **Deps done** = audit clean or every finding triaged with owner + expiry.
- A security claim without its probe output is an opinion, not a control.
