---
name: elasticsearch-opensearch
description: Use for Elasticsearch or OpenSearch — index mappings, text vs keyword, search queries, aggregations, pagination past 10k, bulk ingestion, zero-downtime reindex via aliases, cluster health, and disk-watermark triage — cluster facts probed from env at runtime.
---

# Elasticsearch / OpenSearch

Probe WHICH engine and version first — the two forks diverge. Everything here works on both unless marked.

## Probe

Auth is whatever the env provides — basic (`-u "$ES_USER:$ES_PASS"`) or `-H "Authorization: ApiKey $ES_API_KEY"`; try the cheap root call to learn which. PS 5.1: `curl.exe`.

```sh
curl -sS "$ES_URL/"                                  # .version.number; .version.distribution == "opensearch" on OS
curl -sS "$ES_URL/_cluster/health?pretty"
curl -sS "$ES_URL/_cat/indices?v&s=store.size:desc"  # what exists, how big
```

## Health traffic light

| Status | Meaning | Action |
|---|---|---|
| green | All shards assigned | none |
| yellow | Replicas unassigned | Single node? Normal — for dev set `PUT /<idx>/_settings {"index":{"number_of_replicas":0}}`. Multi-node: `GET /_cluster/allocation/explain` |
| red | Primary shards missing — data unavailable | Stop writes, `allocation/explain`, check disk + node list. Never "fix" red by deleting indices without a snapshot decision |

Never report yellow/red as "working" — name the color and the cause.

## Mappings — decide, don't default

- `text` = analyzed, for full-text matching. `keyword` = exact value, for filter/sort/aggs. Dynamic mapping maps every string BOTH ways (`field` + `field.keyword`) — convenient, doubles storage; fine for logs, wrong for a product index.
- Production indices: explicit mapping + `"dynamic": "strict"` — typo'd fields become errors, not silent garbage columns.
- **Mappings are immutable per field.** Changing one = new index + reindex + alias swap (below). Plan the alias from day one.

| Verbatim output | Fix |
|---|---|
| `Fielddata is disabled on text fields by default` | You aggregated/sorted on `text` — use the `.keyword` subfield or remap. Do NOT enable fielddata (heap trap) |
| `mapper_parsing_exception ... failed to parse field [x] of type [date]` | Dynamic mapping guessed `date` from the first doc; a later doc broke it — explicit mapping |
| `index_not_found_exception` | Typo or alias not created — `GET /_cat/aliases?v` |

## Search essentials

```json
GET /products/_search
{ "query": { "bool": {
    "must":   [ { "match": { "title": "wireless headset" } } ],
    "filter": [ { "term":  { "status": "active" } },
                { "range": { "price": { "gte": 10, "lt": 100 } } } ] } },
  "sort": [ { "_score": "desc" }, { "id": "asc" } ],
  "size": 20 }
```

- `filter` context: cached, no scoring — every exact/range condition goes here; `must` only where relevance matters.
- `match` analyzes the query text; `term` does not. `term` on a `text` field almost never matches a full phrase — the single most common "search returns nothing" cause.

## Pagination

`from + size` is hard-capped. Verbatim:

```
Result window is too large, from + size must be less than or equal to: [10000]
```

Deep paging/export = `search_after`: sort with a unique tiebreaker (`[{"created_at":"desc"},{"id":"asc"}]`), pass the last hit's sort values as `search_after` in the next request, loop until empty. On Elasticsearch pair it with a point-in-time (PIT) for a stable snapshot; plain `search_after` works on both engines.

## Aggregations

- `terms` aggs run on `keyword` fields. Default bucket `size` is **10** — silent truncation; set `size` and check `sum_other_doc_count` for what you dropped.
- `cardinality` is approximate (~0.5% at high cardinality) — say "approx" when reporting it.
- Paging ALL buckets = `composite` aggregation with `after`.
- Time series = `date_histogram` with `calendar_interval`.

## Bulk ingestion — HTTP 200 lies

`_bulk` takes NDJSON action/doc pairs and returns **200 even when every item failed**. The truth is in the body:

```sh
curl -sS -H 'Content-Type: application/x-ndjson' --data-binary @batch.ndjson "$ES_URL/_bulk" \
  | grep -o '"errors":[a-z]*'        # "errors":false = all good; true → inspect items[].status >= 300
```

- Numeric: batch 1,000–5,000 docs or ~5MB per request.
- Mass loads: `"refresh_interval": "-1"` and `number_of_replicas: 0` during the load, restore both after.
- Tests that read-after-write: `POST /<idx>/_refresh` first — near-real-time means ~1s lag by default.

## Zero-downtime mapping change (reindex + alias)

1. Apps talk to an **alias**, never a raw index name — if they don't yet, that migration is step 0.
2. `PUT /products_v2` with the new mapping.
3. `POST /_reindex {"source":{"index":"products_v1"},"dest":{"index":"products_v2"}}` — for big indices add `wait_for_completion=false` and poll `GET /_tasks/<id>`.
4. Atomic swap:

```json
POST /_aliases
{ "actions": [
  { "remove": { "index": "products_v1", "alias": "products" } },
  { "add":    { "index": "products_v2", "alias": "products" } } ] }
```

5. Keep v1 until v2 soaks clean, then delete.

## Disk watermarks — the classic outage

Defaults: **85%** disk = no new shards allocated; **90%** = shards relocate away; **95%** = flood stage, indices forced read-only. Verbatim (modern):

```
cluster_block_exception ... blocked by: [TOO_MANY_REQUESTS/12/disk usage exceeded flood-stage watermark, index has read-only-allow-delete block]
```

(older builds: `FORBIDDEN/12/index read-only / allow delete (api)`)

Fix in this order: free disk (delete old indices, grow volume) — THEN clear the block:

```json
PUT /_all/_settings
{ "index.blocks.read_only_allow_delete": null }
```

Clearing without freeing disk = the block comes straight back.

## More errors → fixes

| Verbatim output | Fix |
|---|---|
| `circuit_breaking_exception ... Data too large` | Query/agg blew the heap breaker — narrow the agg (composite paging, smaller `size`), fewer fields, or more heap |
| `version_conflict_engine_exception` | Concurrent update to the same doc — retry with `retry_on_conflict`, or use `_update` with a partial doc |
| `illegal_argument_exception ... [search_after] ... same sort` | `search_after` values don't match the sort spec — one value per sort clause, same order |

## Done-gates

- **Mapping done** = new docs index cleanly AND a search + an agg return expected results **via the alias**.
- **Bulk load done** = `"errors":false` (or per-item failures handled + retried) AND `GET /<idx>/_count` matches the source count.
- **Reindex done** = v2 count = v1 count, alias swapped, one spot query returns identical results, v1 retained until soak passes.
- **Cluster claim done** = you name the health color and, if not green, why and what's next.
