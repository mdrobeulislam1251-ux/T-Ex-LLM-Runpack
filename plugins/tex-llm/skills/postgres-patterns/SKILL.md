---
name: postgres-patterns
description: Use for any Postgres task — writing queries, schema design, indexes, EXPLAIN triage of slow SQL, migrations, or backup/restore — with connection facts probed from DATABASE_URL/PG* env vars at runtime, never assumed.
---

# Postgres Patterns

Portable Postgres doctrine. Which server you are talking to is PROBED, never assumed — no host, port, database name, or credential appears in this file or in anything you produce.

## Connection — probe before anything else

Connection info comes from the environment: `DATABASE_URL`, or the libpq vars (`PGHOST`, `PGPORT`, `PGUSER`, `PGDATABASE`). Passwords come from `PGPASSFILE` — default `~/.pgpass` (POSIX, mode 0600) or `%APPDATA%\postgresql\pgpass.conf` (Windows) — never inline in a command and never left in shell history inside a `postgres://user:password@` URL.

Check which vars are set (report the NAMES only — `DATABASE_URL` values contain secrets, don't echo them):

```powershell
# PowerShell
Get-ChildItem Env: | Where-Object Name -match '^(DATABASE_URL|PGHOST|PGPORT|PGUSER|PGDATABASE|PGPASSFILE)$' | Select-Object Name
```
```sh
# POSIX
env | grep -oE '^(DATABASE_URL|PGHOST|PGPORT|PGUSER|PGDATABASE|PGPASSFILE)=' | sort
```

With libpq vars set, bare `psql` connects with no arguments. With only `DATABASE_URL`: `psql "$DATABASE_URL"` (POSIX) / `psql $env:DATABASE_URL` (PowerShell). With neither: STOP and ask where the database lives — do not guess localhost.

**Identity probe** — run before any real work, and again after any tunnel/container restart:

```sql
SELECT version(), current_database(), current_user, inet_server_addr(), inet_server_port();
```

`inet_server_addr()` = NULL means a Unix-socket connection (server is local). An unexpected version or database name means you are on the wrong server — stop before writing anything.

### Connection errors → fixes

| Verbatim output (tail) | Fix |
|---|---|
| `connection to server ... failed: Connection refused` | Nothing listening at that host:port — wrong `PGHOST`/`PGPORT`, or the tunnel/container is down. Probe the port first, don't retry blindly. |
| `FATAL:  password authentication failed for user "<user>"` | Missing/wrong pgpass entry. Format: `host:port:db:user:password`, one per line, file mode 0600 on POSIX. |
| `FATAL:  database "<name>" does not exist` | `PGDATABASE` points at the wrong DB — list real ones with `psql -l`. |
| `connection to server on socket ... failed: No such file or directory` | No local server and no `PGHOST` set — export `PGHOST`/`DATABASE_URL`. |
| `FATAL:  no pg_hba.conf entry ... no encryption` | Server requires TLS — add `sslmode=require` to the URL / `PGSSLMODE=require`. |

## Schema conventions

- Tables: plural snake_case (`contacts`, `order_line_items`). FKs: `<other_table_singular>_id`.
- PKs: `id uuid primary key default gen_random_uuid()` (built-in since PG13; older servers need `pgcrypto`). Use `bigint generated always as identity` when insert-order locality matters more than global uniqueness.
- Timestamps: `created_at timestamptz not null default now()`, `updated_at` likewise + trigger. Always `timestamptz`, never bare `timestamp`.
- Booleans prefixed `is_` / `has_`. Enums: `CREATE TYPE ... AS ENUM` or a lookup table — pick one per project and stick with it.
- Strings: default to `text` and enforce limits with a CHECK — `email text NOT NULL CHECK (char_length(email) <= 320)`. In Postgres, `text` and `varchar(n)` perform identically, and a CHECK can be replaced online (add `NOT VALID`, then `VALIDATE`) while shrinking `varchar(n)` forces a full-table validation scan. `varchar(n)`/`char(n)` remain fine when an external standard fixes the length (ISO country `char(2)`, currency `char(3)`).

## Query patterns

- CTEs (`WITH`) over deeply nested subqueries; alias every joined table; `SELECT` explicit columns, never `*` in production; `LIMIT` every ad-hoc query; parameterize everything — never concatenate user input into SQL.

### Keyset pagination (never OFFSET on large tables)
```sql
-- first page
SELECT id, email, created_at FROM contacts ORDER BY created_at DESC, id DESC LIMIT 50;

-- next page (pass the last row's values)
SELECT id, email, created_at FROM contacts
WHERE (created_at, id) < ($1, $2)
ORDER BY created_at DESC, id DESC LIMIT 50;
```
The composite tuple comparison `(created_at, id) < ($1, $2)` is the load-bearing part — it stays correct across duplicate timestamps and uses a `(created_at DESC, id DESC)` index.

### Upsert with inserted-flag
```sql
INSERT INTO contacts (email, name, source)
VALUES ($1, $2, $3)
ON CONFLICT (email) DO UPDATE
  SET name = EXCLUDED.name, updated_at = now()
RETURNING id, (xmax = 0) AS inserted;
```
`(xmax = 0)` is true only for freshly inserted rows — one round-trip tells you insert vs update.

### Conditional aggregation with FILTER
```sql
SELECT campaign_id,
       count(*) FILTER (WHERE status = 'bounced') AS bounces,
       count(*) FILTER (WHERE status = 'opened')  AS opens
FROM events
WHERE occurred_at >= now() - interval '7 days'
GROUP BY campaign_id;
```

### Latest-row-per-group with a window function
```sql
SELECT email, verified_at,
       row_number() OVER (PARTITION BY domain ORDER BY verified_at DESC) AS rn
FROM contacts;
-- outer query: WHERE rn = 1 → most recent per domain
```

## Index rules

1. **Filter columns** in `WHERE` on large tables → B-tree.
2. **Join columns (foreign keys)** — Postgres does NOT auto-index FK columns; every FK you add gets an explicit index unless proven cold.
3. **Sort columns** in `ORDER BY` → B-tree, `DESC` in the index if always descending.
4. **Lowercased text lookup** → functional index: `CREATE INDEX ON contacts (lower(email));` — only used when the query also says `lower(email) = ...`.
5. **Hot subsets** → partial index: `CREATE INDEX ON orders (status) WHERE status = 'pending';`

Don't:
- Index "just in case" — every index taxes every write.
- B-tree a column with <5 distinct values — use a partial index on the hot value instead.
- Duplicate: `(a)` is redundant when `(a, b)` exists (leading-column rule).

Inventory check:
```sql
SELECT tablename, indexname, indexdef FROM pg_indexes
WHERE schemaname = 'public' ORDER BY tablename;
```

## EXPLAIN triage

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) <query>;
```

| Read-out | Meaning → action |
|---|---|
| `Seq Scan on <big table>` in a hot-path query | Missing/unusable index. Check the predicate matches an index (incl. `lower()` wrapping). Ad-hoc one-offs on small tables: fine, ignore. |
| `rows=1000` vs `(actual ... rows=250000)` — off by >10x | Stale planner stats → `ANALYZE <table>;` and re-explain before touching anything else. |
| `Rows Removed by Filter: <huge N>` | Index served the wrong predicate — push the filter column into the index (composite or partial). |
| `Buffers: shared read=<high>` on repeated runs | Working set exceeds cache — a data-volume problem, not a query bug. Don't "fix" the SQL first. |
| `Sort Method: external merge  Disk: <N>kB` | Sort spilled to disk — add an index matching the `ORDER BY`, or `SET work_mem = '64MB'` for that session. |
| `ERROR:  canceling statement due to statement timeout` | Hit `statement_timeout`. Diagnose with EXPLAIN, don't just raise the timeout. |

## Migrations — expand/contract doctrine

Use a real tool (alembic, dbmate, drizzle-kit, prisma migrate, Flyway — whatever the repo already uses; probe for its config before choosing). Files timestamped `YYYYMMDDHHMM_<description>` with both up and down. Never hand-edit a live schema.

Every schema change on a live database runs in two phases — never one:

1. **EXPAND (additive, safe to deploy anytime):** add the new nullable column/table/index. Old code keeps working untouched.
2. **Backfill in batches** — never one full-table UPDATE on a live table:
   ```sql
   UPDATE contacts SET new_col = <expr>
   WHERE id IN (SELECT id FROM contacts WHERE new_col IS NULL LIMIT 10000);
   -- loop until 0 rows affected
   ```
3. **Enforce without a long lock:** `ADD CONSTRAINT c CHECK (new_col IS NOT NULL) NOT VALID;` then `VALIDATE CONSTRAINT c;` (no full write-lock), then `SET NOT NULL` (PG12+ reuses the validated check — no table scan), then drop the redundant check.
4. **Switch** reads/writes to the new column in a code deploy.
5. **CONTRACT in a LATER release:** drop the old column only after the switch has run clean in production. Never drop and switch in the same deploy — that removes your rollback.

Hard rules:
- `SET lock_timeout = '5s';` as the first statement of every DDL migration. `ALTER TABLE` queues behind any long transaction, and every other query then queues behind IT — fail fast instead.
- `CREATE INDEX CONCURRENTLY` on any table you can't afford to lock. It cannot run inside a transaction block, and a failed run leaves an INVALID index: check `SELECT indexrelid::regclass FROM pg_index WHERE NOT indisvalid;`, drop it, retry.
- Never rename a live column/table in one step — that is an expand/contract with dual columns or a view.
- Column type changes that rewrite the table (`ALTER TYPE` incompatible casts) follow the same two-phase path via a new column.

## Backup & restore (before any destructive change)

Connection comes from the same PG* env vars — no credentials in the command line.

```sh
# POSIX
: "${PGDATABASE:?PGDATABASE not set}"
dump="${PGDATABASE}-$(date +%Y%m%d-%H%M).dump"
pg_dump -Fc -f "$dump" && pg_restore -l "$dump" > /dev/null && echo "TOC-OK $dump"
```
```powershell
# PowerShell
if (-not $env:PGDATABASE) { throw 'PGDATABASE not set' }
$dump = "$($env:PGDATABASE)-$(Get-Date -Format yyyyMMdd-HHmm).dump"
pg_dump -Fc -f $dump
pg_restore -l $dump | Out-Null; if ($?) { "TOC-OK $dump" }
```

**BACKUP GATE:** a backup counts only when the file exists with size > 0 AND `pg_restore -l <file>` exits 0. Before any destructive DDL or restore, this gate must have passed within the last hour — otherwise take a fresh dump first.

Restore (prefer a scratch DB first — `createdb ${PGDATABASE}_verify` — before touching the real one):
```sh
pg_restore --clean --if-exists -d "$PGDATABASE" "<file>.dump"
```

| Verbatim output | Fix |
|---|---|
| `pg_dump: error: server version: 16.x; pg_dump version: 14.x` ... `aborting because of server version mismatch` | Client older than server — install a pg_dump ≥ the server's major version. |
| `pg_restore: error: unsupported version (1.xx) in file header` | Dump written by a newer pg_dump than this pg_restore — use a matching or newer client. |

## Anti-patterns to reject on sight

- `timestamp` without time zone → always `timestamptz`.
- `money` type → `numeric(precision, scale)`.
- JSON blobs where a table would do — `jsonb` only for genuinely dynamic schema; everything you'll ever filter or join on gets a real column.
- `SELECT COUNT(*)` to test emptiness → `SELECT EXISTS(SELECT 1 FROM ... )`.
- Mixed-case emails stored raw → `lower(email)` on write and on lookup (pairs with index rule 4).
- `OFFSET` pagination past page ~20 → keyset (above).
- `BETWEEN` on timestamp ranges → half-open `>= start AND < end` (BETWEEN double-counts the boundary).
- Soft-delete `is_deleted boolean` without a filtering view or RLS — someone will forget the WHERE.

## Done-gates

- **Query fix done** = `EXPLAIN (ANALYZE, BUFFERS)` shows the intended plan (no hot-path Seq Scan, estimates within ~10x of actual) — not "returned the right rows once".
- **Migration done** = up applied against a real database, app queries still pass, down tested at least on a scratch DB.
- **Backup done** = BACKUP GATE passed (file > 0 bytes, `pg_restore -l` exit 0). "pg_dump exited 0" alone is "dumped, not verified".
