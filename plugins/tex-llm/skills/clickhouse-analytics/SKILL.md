---
name: clickhouse-analytics
description: Use for ClickHouse — MergeTree table design (ORDER BY, partitioning), batch ingestion, "too many parts" and memory-limit errors, dedup with ReplacingMergeTree, mutations, materialized-view rollups, and system-table triage — server facts probed at runtime.
---

# ClickHouse Analytics

OLAP, not OLTP: append huge batches, scan few columns fast. What kills it: row-by-row inserts, point updates, `SELECT *`.

## Probe

```sh
curl -sS "$CLICKHOUSE_URL/ping"                                  # → Ok.
echo 'SELECT version()' | curl -sS "$CLICKHOUSE_URL/" --data-binary @-   # auth: X-ClickHouse-User / X-ClickHouse-Key headers from env
clickhouse-client --query "SELECT version()"                     # if the native client is installed
```

Then look around: `SHOW DATABASES; SHOW TABLES;` and table sizes (system-table triage below) before designing anything.

## MergeTree doctrine

```sql
CREATE TABLE events (
  event_date Date,
  event_time DateTime('UTC'),
  site_id    UInt32,
  user_id    UInt64,
  name       LowCardinality(String),
  props      String            -- JSON as String; promote hot fields to real columns
) ENGINE = MergeTree
PARTITION BY toYYYYMM(event_date)
ORDER BY (site_id, name, event_time);
```

- **`ORDER BY` IS the primary index** (sparse, on-disk sort order). Equality-filtered, lower-cardinality columns first, time last. It is about data layout, not output order.
- `PARTITION BY` coarse — month is the default choice. A partition is the drop/replace unit. Numeric: keep active parts per table **< ~1000** and partitions in the hundreds, not thousands.
- `LowCardinality(String)` for < ~10k distinct values (status, country, event name) — large compression + speed win.
- `Nullable(T)` costs a hidden mask column — default to non-null with a sentinel where sane.

## Ingestion — batch or die

**1 INSERT = 1 on-disk part.** Tiny frequent inserts explode the part count. Verbatim:

```
DB::Exception: Too many parts (N). Merges are processing significantly slower than inserts. (TOO_MANY_PARTS)
```

- Numeric: ≥ 1,000 rows per INSERT minimum; 10k–500k typical. Many small writers you can't batch → `async_insert = 1` (add `wait_for_async_insert = 1` to keep the delivery guarantee).
- Watch merge pressure: `SELECT count() FROM system.merges;` and parts trend (triage below).
- File loads: `clickhouse-client --query "INSERT INTO events FORMAT CSVWithNames" < data.csv`; over HTTP use `FORMAT JSONEachRow`.
- Design loads idempotent anyway (`data-pipelines`) — dedup-on-retry is not a ClickHouse gift outside replicated block dedup.

## There is no UPDATE — plan around it

- `ALTER TABLE ... UPDATE/DELETE` is an asynchronous **mutation** that rewrites whole parts. Issuing it is "requested", not "applied": check `SELECT * FROM system.mutations WHERE NOT is_done;` — a stuck mutation blocks everything behind it (`KILL MUTATION WHERE mutation_id = '...'`).
- Current-state-per-entity pattern: `ReplacingMergeTree`:

```sql
CREATE TABLE entities (
  entity_id  UInt64,
  status     LowCardinality(String),
  updated_at DateTime('UTC')
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY entity_id;
```

Replacement happens **at merge time — eventually, not on insert**. Reads must still dedup:

```sql
SELECT entity_id, argMax(status, updated_at) AS status
FROM entities GROUP BY entity_id;          -- fast, always correct
-- or: SELECT ... FROM entities FINAL;     -- simple, slower on big tables
```

Gate: any read of a ReplacingMergeTree without `FINAL`/`argMax` is a bug waiting for a merge schedule.

## Rollups with materialized views

```sql
CREATE TABLE daily_stats (
  day     Date,
  site_id UInt32,
  views   UInt64
) ENGINE = SummingMergeTree
ORDER BY (site_id, day);

CREATE MATERIALIZED VIEW mv_daily TO daily_stats AS
SELECT toDate(event_time) AS day, site_id, count() AS views
FROM events GROUP BY day, site_id;
```

- An MV fires on **INSERT only** — history needs a one-time manual `INSERT INTO daily_stats SELECT ...` backfill.
- Summing happens at merge time → always query with `sum(views) GROUP BY` anyway (same eventual-merge rule as above).
- Distinct counts and quantiles in rollups: `AggregatingMergeTree` + `-State` in the MV, `-Merge` at read (`uniqState` → `uniqMerge`).

## Query patterns

- `count()` not `count(*)`. `uniq(x)` is approximate (~2%); `uniqExact(x)` exact but heavy — name which one your numbers used.
- `EXPLAIN indexes = 1 SELECT ...` shows granules read vs total — a "keyed" query reading all granules means the filter doesn't match the `ORDER BY` prefix.
- Huge string columns in a filtered scan: move the filter to `PREWHERE` if it isn't auto-moved.
- Exploration on big tables: `SAMPLE 0.1` (requires `SAMPLE BY` in the DDL).

## Errors → fixes

| Verbatim (stable core) | Fix |
|---|---|
| `Too many parts (N)` — code 252 | Batch bigger / `async_insert`; check `system.merges` keeping up; partitioning too fine is the other cause |
| `Memory limit (for query) exceeded` — code 241 | Wide GROUP BY/JOIN — set `max_bytes_before_external_group_by` (≈ half of `max_memory_usage`) to spill to disk; select fewer columns; pre-aggregate |
| `Missing columns: 'x' while processing query` | ClickHouse alias scoping differs from standard SQL — qualify the column or wrap in a subquery |
| `Table is in readonly mode` | Replicated table lost ZooKeeper/Keeper — fix the Keeper session first, the table heals after |

## System-table triage

```sql
-- slowest recent queries
SELECT query_duration_ms, read_rows, formatReadableSize(memory_usage) AS mem, substring(query, 1, 120) AS q
FROM system.query_log
WHERE type = 'QueryFinish' AND event_time > now() - INTERVAL 1 HOUR
ORDER BY query_duration_ms DESC LIMIT 10;

-- table sizes on disk
SELECT table, formatReadableSize(sum(bytes_on_disk)) AS size
FROM system.parts WHERE active GROUP BY table
ORDER BY sum(bytes_on_disk) DESC;

-- parts pressure (early warning for TOO_MANY_PARTS)
SELECT table, count() AS active_parts
FROM system.parts WHERE active GROUP BY table
HAVING active_parts > 500 ORDER BY active_parts DESC;
```

## Done-gates

- **Schema done** = a realistic-volume query shows granule pruning in `EXPLAIN indexes = 1` (reads ≪ total) — "returns rows on 100 test rows" proves nothing.
- **Ingestion done** = sustained load with a stable active-part count across 3 checks — not one successful insert.
- **Dedup design done** = an entity updated twice returns exactly one row via `FINAL`/`argMax`.
- **Mutation done** = `system.mutations` shows `is_done = 1` — never report an ALTER as applied before that.
