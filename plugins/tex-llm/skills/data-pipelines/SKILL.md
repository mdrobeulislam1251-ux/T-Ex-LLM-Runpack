---
name: data-pipelines
description: Use for ETL/ELT work — incremental loads, high-watermark extraction, backfills, dedup at load, idempotent upserts, checkpointing, late-arriving data, and post-load validation gates — orchestrator-agnostic (cron, Airflow, Prefect, or plain scripts, probed from the repo).
---

# Data Pipelines

Doctrine: every pipeline is **idempotent, incremental, resumable, observable**. Re-runs are not the exception — they are the operating mode. A pipeline that can't be safely re-run isn't done.

## Probe

What already orchestrates here? Look for `dags/`, `flows/`, cron entries, workflow YAML, `package.json`/`Makefile` targets named etl/sync/load. Read one existing job end-to-end and match its checkpointing and naming — don't introduce a second convention.

## Incremental load — high-watermark pattern

```sql
-- state table (one row per job)
CREATE TABLE IF NOT EXISTS etl_state (
  job_name   text PRIMARY KEY,
  watermark  timestamptz NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- extract: half-open window with a lag guard for in-flight commits
SELECT * FROM source_rows
WHERE updated_at >  $last_watermark
  AND updated_at <= now() - interval '5 minutes'
ORDER BY updated_at, id;
```

- New watermark = **MAX(updated_at) of the rows actually loaded** — never `now()`. Using `now()` silently skips anything that commits after the query ran.
- Numeric: lag window ≥ max observed commit/replication lag; start at 5 minutes and tune with evidence.
- The watermark column must be indexed on the source — an incremental job that full-scans the source isn't incremental.

## Idempotent load — pick ONE mechanism, always

1. **Upsert by natural key** — `INSERT ... ON CONFLICT (key) DO UPDATE` (pattern in `postgres-patterns`).
2. **Partition swap** — load into staging, then atomically replace the window:

```sql
BEGIN;
DELETE FROM target WHERE event_date = $d;
INSERT INTO target SELECT * FROM staging_day;
COMMIT;
```

3. **Append-only + dedup view** — allowed only when readers use the view.

If you cannot name which of the three a pipeline uses, it isn't idempotent — a retry after a half-failure will double rows.

Dedup at load (latest version wins):

```sql
INSERT INTO clean
SELECT * FROM (
  SELECT s.*, row_number() OVER (PARTITION BY natural_key ORDER BY updated_at DESC, id DESC) AS rn
  FROM staged s
) t WHERE rn = 1;
```

## Backfill discipline (backfill ≠ incremental run)

- Chunk by time window, sized so one chunk takes ≤ ~5 minutes; loop oldest → newest.
- Checkpoint every chunk so a kill resumes instead of restarting:

```sql
CREATE TABLE IF NOT EXISTS backfill_chunks (
  job_name    text,
  chunk_start timestamptz,
  chunk_end   timestamptz,
  status      text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','done','failed')),
  rows_loaded bigint,
  finished_at timestamptz,
  PRIMARY KEY (job_name, chunk_start)
);
```

- Resume = process `WHERE status <> 'done'`. Re-running a chunk stuck in `running` must converge — that's the idempotency rule doing its job.
- Rate-limit against the live source: pause between chunks, run off-peak; the backfill must never degrade production reads.
- **Same transform function as the incremental path.** Two code paths = backfilled history that disagrees with daily data, discovered months later.

## Time doctrine

- Store UTC (`timestamptz`) everywhere; convert only at display.
- Windows are half-open `[start, end)` — `BETWEEN` double-counts boundaries.
- Late data: pick a strategy and WRITE IT DOWN — either reprocess a trailing window nightly (common: 3 days), or watermark on ingestion time and keep event time as a column.

## Validation gates — run mechanically after EVERY load

| Gate | Check | Threshold |
|---|---|---|
| Volume | loaded rows vs source count, same window | mismatch > 0.5% = fail |
| Uniqueness | `count(*) - count(DISTINCT natural_key)` | must be 0 |
| Nulls | null rate on critical columns | > 0.1% = fail (tune per column) |
| Freshness | `now() - max(event_time)` | > 2× schedule interval = alert |
| Reconciliation | `sum(metric)` per day vs source | drift > 1% = investigate before the next run |

A failed gate marks the run failed and the watermark does NOT advance. A green run with bad data is worse than a red run — red gets fixed, green gets trusted.

## Failure & retry

- Transient failures (network, lock timeout): 3 retries, exponential backoff (1m → 5m → 25m).
- Data failures (schema drift, constraint violation): **zero retries** — they need a human; retrying corrupts.
- Extracts name explicit columns (`SELECT a, b, c`, never `SELECT *`) so upstream schema changes become a controlled failure, not silent drift.
- Every run logs: rows in/out, watermark before/after, duration, gate results. A pipeline you can't interrogate at 3am isn't observable.

## Anti-patterns

- `TRUNCATE` + reload of a live table — readers see it empty; stage + swap in one transaction instead.
- `now()` as the new watermark. `SELECT *` extracts. Local-time timestamps.
- Retrying constraint violations until they "pass".
- Exit 0 after loading 80% ("partial success") — partial is failure with a checkpoint.
- A dedup step downstream of a load that should have been idempotent upstream.

## Done-gates

- **Pipeline done** = ran twice back-to-back → target state identical (zero new duplicates); killed mid-run and re-run → converges; all validation gates pass; state table shows the advanced watermark.
- **Backfill done** = every chunk `done`, spot reconciliation on 3 random historical windows inside threshold, and the regular incremental still runs clean afterwards.
