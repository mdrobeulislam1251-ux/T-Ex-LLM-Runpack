---
name: fleet-app-hosting
description: Use to deploy/host an application on the right server in an SSH fleet and expose it correctly — routing the app to the best-fit host by role and capacity, deploying over local SSH (docker compose / systemd / pm2 / static), and exposing it the RIGHT way (reverse proxy or outbound tunnel + TLS, never 0.0.0.0, never the database). Works with the local ~/.ssh/config; state-changing steps run through server-ops-safety.
---

# Fleet App Hosting

Turns "the app is built" into "the app is live at a URL, safely". Three jobs in order: **route** it to the right box, **deploy** it over local SSH, **expose** it through exactly one correct front door. Every state-changing step drops to `server-ops-safety`'s gates on the target box.

## Works with your local SSH

Everything runs through `~/.ssh/config` aliases — `ssh <alias>`, `scp`, `rsync -e ssh`, `docker -H ssh://<alias>`. No cloud provider API. Tailscale-SSH or key-based both work; the connect gotchas live in `server-fleet-management`. Read the fleet registry (`fleet-registry.json`, or the `.example` template) + `~/.ssh/config` to know the boxes — never hardcode a host.

## Step 1 — Route to the right host

Pick the box by ROLE and CAPACITY, not habit. Read the registry, then confirm live:

| App needs | Route to a host whose role is | Never put it on |
|---|---|---|
| Web app / API (stateless) | `app` — has CPU/RAM headroom | a `data` box flagged high-RAM, or the DB box |
| Background workers / queues | `app` or a dedicated worker box | the edge/proxy box |
| Static site / SPA | `edge` (proxy box) or object storage + CDN | anywhere with a live DB |
| Anything GPU/model | `ai` box | a general app box |

Routing rules:
- **Capacity gate first.** A box flagged high-RAM / high-load / near-full is observe-only — do not deploy there without explicit user approval AND re-verified headroom this session (`free -h`, `df -h /`).
- **Co-locate with data only when latency demands it** and the box has room; otherwise app and DB stay on separate boxes and talk over the tailnet/private interface.
- Confirm the chosen box's identity live (`hostnamectl`) before touching it — roles drift.

## Step 2 — Deploy over local SSH

Get the artifact onto the box and running, bound to **localhost or a high port** (exposure is Step 3, deliberately separate). Pick the method the box already uses (probe: `docker ps`, `pm2 list`, `systemctl`):

**Docker Compose (preferred for anything with dependencies):**
```sh
# ship code without .git/node_modules; secrets travel as an env file, not in the image
rsync -az --delete -e ssh --exclude='.git' --exclude='node_modules' ./ <alias>:/opt/<app>/
ssh <alias> 'cd /opt/<app> && docker compose pull && docker compose up -d'
ssh <alias> 'cd /opt/<app> && docker compose ps'      # every service healthy?
```
Compose must bind app ports to `127.0.0.1:` (`"127.0.0.1:8080:8080"`) — a bare `8080:8080` publishes on all interfaces AND bypasses ufw. DB/cache services get no `ports:` at all (reachable inside the compose network only).

**systemd (single binary / non-containerized):**
```sh
rsync -az -e ssh ./dist/ <alias>:/opt/<app>/
ssh <alias> 'sudo systemctl daemon-reload && sudo systemctl restart <app> && systemctl is-active <app>'
```
Unit runs as a non-root service user, `WorkingDirectory` set, `EnvironmentFile=/opt/<app>/.env` (mode 600) — never inline secrets in the unit.

**pm2 (node fleets that already use it):**
```sh
ssh <alias> 'cd /opt/<app> && pm2 startOrReload ecosystem.config.js && pm2 save'
```

**Secrets to the box (never through git, never on the command line):**
```sh
scp ./.env.production <alias>:/opt/<app>/.env      # then: ssh <alias> 'chmod 600 /opt/<app>/.env'
```

State-changing deploys follow `server-ops-safety`: backup what you replace, one change, health-check, and write the rollback line first (`rollback = docker compose down && restore /opt/<app>.bak && up -d`).

## Step 3 — Expose the RIGHT way

The app is answering on `127.0.0.1:<port>`. Now exactly ONE front door — decided by the table, never by publishing on `0.0.0.0`:

| Situation | Front door | Why |
|---|---|---|
| Public site/app, box HAS public inbound 443 | Reverse proxy (Caddy/nginx) + TLS on the edge box | Standard; origin stays localhost |
| Public site/app, box has NO public inbound (NAT/firewall) | Outbound tunnel (cloudflared / newt) → localhost | Dials out; no inbound port needed |
| Internal tool, team only | Tailscale-only (bind tailnet IP, or proxy on the tailnet) | Never hits the public internet |
| A database/admin panel/metrics | **Not exposed.** SSH tunnel on demand: `ssh -L 5432:127.0.0.1:5432 <alias>` | Data stores never get a public front door |

**Caddy** (automatic HTTPS — simplest correct default):
```
app.example.com {
    reverse_proxy 127.0.0.1:8080
}
```
**nginx** (proxy to localhost; TLS via certbot or the Cloudflare origin cert):
```
server {
    server_name app.example.com;
    location / { proxy_pass http://127.0.0.1:8080; proxy_set_header Host $host; }
    listen 443 ssl;   # certs by certbot / origin cert
}
```
Validate before reload: `nginx -t` / `caddy validate` (fails → fix, don't reload).

**Cloudflared tunnel** (box with no public inbound):
```yaml
# /etc/cloudflared/config.yml — ingress maps hostname → localhost service
ingress:
  - hostname: app.example.com
    service: http://127.0.0.1:8080
  - service: http_status:404
```
```sh
ssh <alias> 'cloudflared tunnel route dns <tunnel-name> app.example.com && systemctl restart cloudflared'
```

**Exposure hard rules:**
- The app binds `127.0.0.1` (or the tailnet IP for internal) — the proxy/tunnel is the only thing on `0.0.0.0:443`.
- TLS always on the public edge — HTTP only between proxy and localhost.
- One hostname → one service. Databases, Redis, admin panels, `/metrics`: never a public hostname (reach them via `ssh -L`).
- Don't lock inbound to tailnet-only on a box whose public sites depend on public 443 — that takes them offline (check the identity doc's ingress section first).

## Step 4 — Verify end to end

```sh
ssh <alias> 'curl -fsS -m 5 http://127.0.0.1:<port>/health'   # 1. app answers locally
curl -fsS -m 10 https://app.example.com/health                # 2. answers through the front door over HTTPS
curl -sSI https://app.example.com | grep -i strict-transport  # 3. TLS + HSTS present
ssh <alias> "ss -tlnp | awk '\$4 ~ /0\\.0\\.0\\.0/'"          # 4. only the proxy/tunnel on 0.0.0.0 — never the app or DB
```
DNS/TLS/tunnel failures → `network-diagnosis`. Exposure that skips the localhost bind (app itself on 0.0.0.0) is a finding even if the URL works.

## Done-gates

- **Hosted done** = app answers on `127.0.0.1:<port>` on the target box AND through its public HTTPS URL, the box was identity-confirmed and capacity-checked, and the rollback line was written before deploy.
- **Exposed done** = TLS valid on the public URL, only the proxy/tunnel listens on `0.0.0.0`, and no data store/admin panel has a public front door (the 0.0.0.0 audit is clean).
- "It deployed" without the through-the-URL HTTPS check is "shipped, not verified".
