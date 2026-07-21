---
name: supabase-platform
description: Use for any Supabase task — auth, Row Level Security policies, PostgREST/supabase-js queries, storage, edge functions, local dev, migrations, or the connection-pooler trap — hosted or self-hosted, with project facts probed from SUPABASE_* env vars at runtime, never assumed.
---

# Supabase Platform

Portable Supabase doctrine. WHICH project you are talking to is probed from env — no project ref, URL, or key appears in this file or in anything you produce.

## Probe before anything

Expected vars (names vary by framework — check all): `SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_URL` / `VITE_SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, plus `DATABASE_URL` for direct Postgres. List names only — values are secrets.

Health probes (PS 5.1: use `curl.exe`, not `curl`):

```sh
curl -sS -o /dev/null -w '%{http_code}\n' "$SUPABASE_URL/auth/v1/health" -H "apikey: $SUPABASE_ANON_KEY"   # 200 = auth up + key accepted
curl -sS -o /dev/null -w '%{http_code}\n' "$SUPABASE_URL/rest/v1/" -H "apikey: $SUPABASE_ANON_KEY"          # 200 = PostgREST up
```

Key identity — decode the JWT payload and check `role`, `exp`, and project `ref` before blaming anything else:

```sh
node -e "const p=process.env.SUPABASE_ANON_KEY.split('.')[1];const c=JSON.parse(Buffer.from(p,'base64url').toString());console.log(c.role, c.ref||c.iss, new Date(c.exp*1000).toISOString())"
```

Hosted vs local: URL ending `.supabase.co` = hosted; `localhost:54321` = the `supabase start` local stack (`supabase status` prints the real ports).

## The two keys — never confuse them

| Key | `role` claim | Where it may live | RLS |
|---|---|---|---|
| anon | `anon` | Browser, mobile, anything public | **enforced** |
| service_role | `service_role` | Server-side only: jobs, webhooks, admin scripts | **bypassed** |

Gate: service_role in client-reachable code is an incident — rotate it, don't just delete the line. Sweep before every release: grep the client bundle/output dir for `SERVICE_ROLE` and for the key's first 10 chars.

## RLS doctrine

Every table in an exposed schema has RLS ON. Inventory the gaps first:

```sql
SELECT c.relname AS table, c.relrowsecurity AS rls_on
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r' ORDER BY 1;
```

Any `rls_on = f` row in `public` is readable/writable with the anon key (grants permitting) — fix before feature work.

The standard owner-only policy set:

```sql
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;
CREATE POLICY notes_select ON notes FOR SELECT USING ((SELECT auth.uid()) = user_id);
CREATE POLICY notes_insert ON notes FOR INSERT WITH CHECK ((SELECT auth.uid()) = user_id);
CREATE POLICY notes_update ON notes FOR UPDATE USING ((SELECT auth.uid()) = user_id) WITH CHECK ((SELECT auth.uid()) = user_id);
CREATE POLICY notes_delete ON notes FOR DELETE USING ((SELECT auth.uid()) = user_id);
```

- `USING` = which existing rows are visible/actionable; `WITH CHECK` = which new/updated rows are accepted. INSERT takes only WITH CHECK; SELECT only USING.
- `(SELECT auth.uid())` instead of bare `auth.uid()` — the subquery is evaluated once per statement instead of per row; matters from ~10k rows.
- Public reference tables: `FOR SELECT USING (true)` — explicit is fine; implicit (RLS off) is not.
- `SECURITY DEFINER` functions run with the OWNER's rights and skip the caller's RLS — always `SET search_path = ''` inside them and grant EXECUTE deliberately.

### RLS / API errors → fixes

| Verbatim output | Fix |
|---|---|
| `new row violates row-level security policy for table "x"` | INSERT/UPDATE failed WITH CHECK — missing INSERT policy, or the payload's `user_id` ≠ `auth.uid()` (set it server-side or via column default) |
| `permission denied for table x` | GRANT missing — RLS filters rows AFTER grants: `GRANT SELECT ON x TO authenticated;` |
| Query returns `[]` though rows exist | No SELECT policy matches. Confirm data exists with the service key, then write the policy — do NOT switch the app to the service key |
| `permission denied for schema x` | Custom schema not exposed — add it to PostgREST's exposed schemas + `GRANT USAGE ON SCHEMA x TO anon, authenticated;` |
| `JWSError JWSInvalidSignature` | Key signed with a different JWT secret — mixed projects, or self-hosted services sharing no secret |
| `PGRST301` / `JWT expired` | Client session expired — refresh the session; also check client clock skew |

## Query patterns (PostgREST / supabase-js)

- Columns + FK embedding: `.select('id, title, author:profiles(name)')`
- `.single()` errors when rows ≠ 1 (`PGRST116`) — use `.maybeSingle()` for 0-or-1.
- Pagination: `.range(0, 49)` (50 rows); counts without rows: `{ count: 'exact', head: true }`.
- Upsert: `.upsert(row, { onConflict: 'email' })`.
- Join-heavy or aggregate reads → a Postgres function + `.rpc('fn', args)` — don't fetch tables to join in JS.

## Connection strings — the pooler trap

| Port | What | Use for |
|---|---|---|
| 5432 | direct Postgres | migrations, `pg_dump`, long sessions |
| 6543 | PgBouncer, transaction mode | app runtime, serverless functions |

Transaction-mode pooling has no session state → prepared statements break. Verbatim classic (Prisma/Drizzle):

```
ERROR: prepared statement "s0" already exists
```

Fix: runtime URL gets `?pgbouncer=true` (Prisma) / `prepare: false` (postgres.js, Drizzle); migrations always run against 5432. Serverless: `connection_limit=1` per instance.

## Storage

- Buckets are private by default; a public bucket means anyone with the URL reads forever — choose deliberately.
- Signed URLs: `createSignedUrl(path, 3600)` — TTL in seconds; sign for an hour, not a week.
- Storage RLS lives on `storage.objects`. Users-own-folder pattern:

```sql
CREATE POLICY avatar_read ON storage.objects FOR SELECT
USING (bucket_id = 'avatars' AND (storage.foldername(name))[1] = (SELECT auth.uid())::text);
```

- Never trust a client-supplied object path — prefix with the user id server-side or enforce it via the policy above.

## Edge functions

- `supabase functions new fn` → `supabase functions serve` (local) → `supabase functions deploy fn`.
- Secrets: `supabase secrets set NAME=value` (from env, never committed); read with `Deno.env.get('NAME')`.
- JWT verification is ON by default — third-party webhook endpoints need `--no-verify-jwt` at deploy and their own signature check instead.
- Invoke check: `curl -sS "$SUPABASE_URL/functions/v1/fn" -H "Authorization: Bearer $SUPABASE_ANON_KEY"`.

## Local dev & migrations

- `supabase init` once, `supabase start` for the local stack; `supabase status` prints actual URLs/ports/keys.
- Schema changes live in `supabase/migrations/*.sql`: `supabase migration new <name>` → write SQL → `supabase db reset` replays all migrations + `seed.sql` clean.
- Made changes in Studio instead? Capture them: `supabase db diff -f <name>` — Studio clicks are not source control.
- Apply to hosted: `supabase link --project-ref <ref-from-env>` then `supabase db push`.

## Done-gates

- **RLS done** = probed WITH THE ANON KEY as two different users: own rows visible, other's rows invisible, cross-user write rejected with the RLS error. Testing with the service key proves nothing (it bypasses RLS).
- **Auth flow done** = full round trip ran: sign-up → session token → authenticated read/write → sign-out invalidates.
- **Migration done** = `supabase db reset` runs clean locally AND the migration file is committed — a schema that exists only in Studio is done-on-one-machine.
- **Edge function done** = deployed invoke returns the expected output via curl, not just `serve` locally.
- **Storage done** = signed URL returns bytes AND an unauthorized fetch fails.
