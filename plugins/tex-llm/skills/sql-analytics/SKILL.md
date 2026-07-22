---
name: sql-analytics
description: Use for analytical SQL — cohort retention, funnels, sessionization, dedup, running totals, period-over-period deltas — and the NULL/join/window traps that silently corrupt results. Dialect is probed first; patterns are portable SQL with Postgres flavor noted.
---

# SQL Analytics

Correctness first: an analytical query that LOOKS right and returns plausible numbers is the most dangerous artifact in data work. Every pattern here ships with its verification check — run it before the numbers leave your hands.

## Probe the dialect first

`SELECT version();` (Postgres/MySQL) · `SELECT @@version;` (SQL Server) · `SELECT sqlite_version();` · ClickHouse `SELECT version();`. Date functions, window-frame defaults, and division semantics differ — confirm before pasting patterns across engines.

## Dedup — find, inspect, remove

```sql
-- find
SELECT natural_key, count(*) FROM t GROUP BY natural_key HAVING count(*) > 1;

-- remove, keep latest (Postgres)
DELETE FROM t a USING t b
WHERE a.natural_key = b.natural_key
  AND (a.updated_at, a.id) < (b.updated_at, b.id);
```

Portable alternative: `row_number()` in a CTE, delete `rn > 1` via the PK. **Verify after:** the find query returns 0 rows.

## Sessionization (gap rule)

```sql
WITH gaps AS (
  SELECT user_id, event_at,
         CASE WHEN lag(event_at) OVER w IS NULL
                OR event_at - lag(event_at) OVER w > interval '30 minutes'
              THEN 1 ELSE 0 END AS new_session
  FROM events
  WINDOW w AS (PARTITION BY user_id ORDER BY event_at)
), numbered AS (
  SELECT *, sum(new_session) OVER (PARTITION BY user_id ORDER BY event_at
                                   ROWS UNBOUNDED PRECEDING) AS session_id
  FROM gaps
)
SELECT user_id, session_id,
       min(event_at) AS started, max(event_at) AS ended, count(*) AS events
FROM numbered GROUP BY 1, 2;
```

30 minutes is the web-analytics convention — state the gap you chose next to the numbers you report.

## Cohort retention

```sql
WITH cohorts AS (
  SELECT user_id, date_trunc('month', min(created_at)) AS cohort_month
  FROM users GROUP BY 1
), activity AS (
  SELECT DISTINCT user_id, date_trunc('month', event_at) AS active_month
  FROM events
)
SELECT c.cohort_month,
       (extract(year  FROM a.active_month) - extract(year  FROM c.cohort_month)) * 12
     +  extract(month FROM a.active_month) - extract(month FROM c.cohort_month)  AS month_n,
       count(DISTINCT a.user_id) AS active_users
FROM cohorts c
JOIN activity a USING (user_id)
WHERE a.active_month >= c.cohort_month
GROUP BY 1, 2 ORDER BY 1, 2;
```

**Verify:** each cohort's `month_n = 0` row must equal that cohort's size. If it doesn't, the join or the cohort definition is wrong — stop.

## Funnel (order-enforced steps)

```sql
WITH s1 AS (
  SELECT user_id, min(event_at) AS t1 FROM events WHERE name = 'signup' GROUP BY 1
), s2 AS (
  SELECT e.user_id, min(e.event_at) AS t2
  FROM events e JOIN s1 ON s1.user_id = e.user_id AND e.event_at > s1.t1
  WHERE e.name = 'activated' GROUP BY 1
), s3 AS (
  SELECT e.user_id, min(e.event_at) AS t3
  FROM events e JOIN s2 ON s2.user_id = e.user_id AND e.event_at > s2.t2
  WHERE e.name = 'purchased' GROUP BY 1
)
SELECT (SELECT count(*) FROM s1) AS signed_up,
       (SELECT count(*) FROM s2) AS activated,
       (SELECT count(*) FROM s3) AS purchased;
```

The `e.event_at > s_prev.t_prev` join condition is the load-bearing part — it enforces step ORDER. **Verify:** counts must be monotonically non-increasing; a later step exceeding an earlier one means the ordering constraint is missing.

## Period over period

```sql
WITH m AS (
  SELECT date_trunc('month', created_at) AS month, count(*) AS n
  FROM orders GROUP BY 1
)
SELECT month, n,
       lag(n) OVER (ORDER BY month) AS prev_n,
       round(100.0 * (n - lag(n) OVER (ORDER BY month))
             / NULLIF(lag(n) OVER (ORDER BY month), 0), 1) AS pct_change
FROM m ORDER BY month;
```

`NULLIF(..., 0)` makes division-by-zero yield NULL instead of an error; `100.0` (not `100`) forces float math — integer division silently floors to 0.

## Running totals — the frame trap

With `ORDER BY`, the default window frame is `RANGE`, which lumps tied order keys together. Running totals want `ROWS`:

```sql
sum(amount) OVER (ORDER BY created_at, id ROWS UNBOUNDED PRECEDING)
```

## The silent-corruption traps

| Trap | Symptom | Fix |
|---|---|---|
| `NOT IN (subquery)` where the subquery can return NULL | Zero rows, no error | `NOT EXISTS`, or filter `IS NOT NULL` inside |
| Join fanout | Metrics inflate after adding a join | Compare `count(*)` before/after; pre-aggregate the many-side. `SELECT DISTINCT` masks the symptom, never fixes it |
| `count(col)` vs `count(*)` | Counts mysteriously low | `count(col)` skips NULLs — use deliberately or not at all |
| `avg(col)` with NULLs | Average too high | Decide: `coalesce(col, 0)` or document the exclusion |
| `BETWEEN` on timestamps | Boundary rows counted twice across periods | Half-open: `>= start AND < end` |
| `GROUP BY 1` ordinals in saved queries | Silent regroup when columns reorder | Column names in anything that persists |
| Mixed time zones | Daily numbers disagree with the dashboard | One declared zone: `date_trunc('day', ts AT TIME ZONE 'UTC')` |
| Integer division | Every ratio is 0 | Multiply by `100.0`, `NULLIF` the denominator |

## Reconciliation gates — before ANY numbers ship

1. **Parts = whole:** segment counts sum to the unsegmented total.
2. **Funnel monotonic:** each step ≤ the previous.
3. **Cohort diagonal:** month-0 actives = cohort size.
4. **Spot-check 3 rows** end-to-end by hand against raw data.
5. **One aggregate vs a known-true source** (billing, the production dashboard).

All five pass → ship. Anything fails → the query is wrong until proven otherwise. Plausible ≠ verified.

## Anti-patterns

- `SELECT DISTINCT` to "fix" inflation (see fanout trap — diagnose the join).
- `OFFSET` beyond ~10k rows for exports — keyset pagination instead (`postgres-patterns`).
- Correlated subquery per row where one window pass does it.
- Magic date literals scattered through a query — one `params` CTE at the top, referenced everywhere.
