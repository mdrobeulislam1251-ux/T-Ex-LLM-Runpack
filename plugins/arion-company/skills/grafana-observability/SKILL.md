---
name: grafana-observability
description: Use for Grafana dashboards, PromQL queries, alert rules and contact points, and provisioning datasources/dashboards as code — instance facts probed from GRAFANA_URL and a service-account token in env at runtime.
---

# Grafana Observability

Dashboards are code, alerts fire on symptoms, every panel has a unit. Which instance you're on is probed, never assumed.

## Probe

```sh
curl -sS "$GRAFANA_URL/api/health"                                                    # {"database":"ok",...} — no auth needed
curl -sS -H "Authorization: Bearer $GRAFANA_TOKEN" "$GRAFANA_URL/api/org"             # 200 = token valid
curl -sS -H "Authorization: Bearer $GRAFANA_TOKEN" "$GRAFANA_URL/api/datasources"     # names + uids you'll reference
```

(PS 5.1: `curl.exe`.) Auth = **service-account token** (Administration → Service accounts); legacy API keys are deprecated. `401` = token bad/expired; `403` = token valid but its role is too low for the call (a Viewer token cannot write dashboards).

## Provision as code — the portable way

Anything clicked together in the UI exists on one instance only. Version everything under `provisioning/`:

```yaml
# provisioning/datasources/prometheus.yaml
apiVersion: 1
datasources:
  - name: Prometheus
    uid: prometheus-main        # PIN the uid — panels reference it
    type: prometheus
    access: proxy
    url: $PROMETHEUS_URL        # env-expanded by Grafana at startup
    isDefault: true
```

```yaml
# provisioning/dashboards/default.yaml
apiVersion: 1
providers:
  - name: default
    folder: Services
    type: file
    options:
      path: /etc/grafana/provisioning/dashboards/json
```

**Pin `uid`** on datasources AND dashboards — auto-generated uids drift between environments and produce `Data source not found` on every imported panel.

API round-trip for dashboards you manage in git:

```sh
# export current state → versioned JSON
curl -sS -H "Authorization: Bearer $GRAFANA_TOKEN" "$GRAFANA_URL/api/dashboards/uid/<uid>" > dash.json
# apply (wrap the dashboard object, bump/remove "version")
curl -sS -X POST -H "Authorization: Bearer $GRAFANA_TOKEN" -H 'Content-Type: application/json' \
  -d '{"dashboard": <dashboard-json>, "folderUid": "<folder>", "overwrite": true}' \
  "$GRAFANA_URL/api/dashboards/db"
```

| Symptom | Fix |
|---|---|
| HTTP `412` `The dashboard has been changed by someone else` | Version conflict — re-GET and reapply, or `overwrite: true` when git is the source of truth |
| `Data source not found` after import | uid drift — pin uids in provisioning; re-point panels at the pinned uid |
| Provisioned dashboard can't be saved in UI | By design — provisioned = read-only in UI; change the JSON in git |

## Dashboard doctrine

- Top row: 4–6 stat tiles answering "is it OK right now". Below: time series, **one question per panel**.
- Per service: **RED** — Rate, Errors, Duration. Per resource: **USE** — Utilization, Saturation, Errors.
- **Every panel gets a unit** (Field → Standard options → Unit) — an unlabeled graph is a rumor. Percent gets min 0 / max 100; bytes as bytes(IEC); durations as seconds.
- Y-axis from zero for rates and areas; deviation-hunting panels may zoom but say so in the panel description.
- Draw thresholds (p95 target, error budget) so "bad" is visible without tribal knowledge.
- Numeric: a service dashboard is **≤ ~12 panels**; more = split by audience (on-call vs deep-dive).

## PromQL core

| Need | Query |
|---|---|
| Request rate | `sum(rate(http_requests_total[5m]))` |
| Error % | `100 * sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` |
| p95 latency | `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))` |
| CPU per instance | `rate(process_cpu_seconds_total[5m])` |
| Memory saturation | `1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes` |

Rules that prevent wrong graphs:
- `rate()` window ≥ **4× scrape interval** (15s scrape → `[1m]` minimum, `[5m]` standard). Shorter windows produce gaps and lies.
- `rate` BEFORE `sum` — summing counters first destroys per-series reset handling.
- `histogram_quantile` needs `sum by (le)` — dropping `le` returns NaN.
- `irate` for spiky close-up debugging only — never in alerts.

**Panel shows "No data" checklist:** time range? panel's datasource? metric name exists (Explore → autocomplete)? label selector matches anything? rate window ≥ 4× scrape?

## Alerting doctrine

- Alert on **symptoms users feel** (error rate, latency, freshness) — causes (CPU, memory) belong on dashboards, not pagers.
- Every rule has `for:` to kill flap — numeric: **5m** standard; `0` only for hard-down detection.
- Two severities only: `critical` = page now; `warning` = ticket. No middle tier that everyone ignores.
- The annotation carries the runbook link and the first query to run — the alert is the start of the diagnosis, not just a noise.
- Numeric starting thresholds: error rate > 1% for 5m = warning, > 5% for 5m = critical (tighten from your SLO); pipeline freshness: `now() - max(event_time)` > 2× the schedule = warning.

## Done-gates

- **Dashboard done** = renders LIVE data in the target environment, every panel has a unit, and the JSON lives in git/provisioning. "Imported once by hand" is done-on-one-instance.
- **Alert done** = you forced it to fire once (temporarily lower the threshold or emit a synthetic series) and the notification ARRIVED at the contact point. An alert that has never fired is decoration.
- **Datasource done** = its health check passes via the API (`/api/datasources/uid/<uid>/health`), not just the UI test button.
