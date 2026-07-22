---
name: server-fleet-management
description: Use when operating a FLEET of servers over SSH (multiple boxes, Tailscale or key-based) — connecting, routing a task to the right host, reading the fleet inventory, running a safe read-first sweep across boxes, and respecting per-box capacity rules. Sits above server-ops-safety (which governs the actual change on one box) and server-identity-builder (which writes the docs).
---

# Server Fleet Management

Operating many machines is a routing-and-verification problem before it is an ops problem. You never act on a box from memory — you read the fleet doc, confirm you're on the RIGHT host this session, then hand the actual change to `server-ops-safety`.

## Fleet doctrine (non-negotiable)

1. **No guess, no trust.** State drifts. Every fact (what's running, which port, how much RAM) comes from a live probe THIS session, not the fleet doc and not last week.
2. **Right box, every time.** Before any command, confirm hostname/identity matches the box you intend (the identity probe below). One `hostnamectl` saved from disaster beats ten careful commands on the wrong server.
3. **Secrets are paths, never values.** Document that `secret.env` exists at a path with mode 600 — never read, print, or copy its contents. This is why the fleet docs are safe to keep.
4. **Capacity rules are hard.** A box flagged high-RAM / high-load in the fleet doc gets read/observe only — no new services, no restarts — without explicit user approval.
5. **Read before write, everywhere.** A fleet sweep is read-only by default. State-changing work drops to `server-ops-safety`'s four gates on that one box.

## Connect — probe the access model first

Fleets use one of: **Tailscale SSH** (identity-based, no keys), key-based SSH, or a bastion. Probe which BEFORE connecting:

```sh
tailscale status 2>/dev/null | head        # tailnet peers + online state, if Tailscale
cat ~/.ssh/config 2>/dev/null | grep -iE '^host |hostname|user'   # aliases already defined
```

**Tailscale-SSH gotcha (verbatim):**

| Output | Cause → fix |
|---|---|
| `failed to look up local user "<you>"` | Bare `ssh <ip>` sent your LOCAL username, which has no account on the box. Tailscale SSH maps by tailnet identity but still needs a valid target user — connect as the account that exists (often `ssh root@<ip>` or the aliased `User`). |
| `ssh: connect to host <ip> port 22: Connection refused` | sshd not listening on that interface, or the box is down — check `tailscale ping <peer>` first; a tailnet address that won't ping is a network problem, not an SSH one. |
| `Permission denied (tailscale)` | Your tailnet identity isn't authorized for SSH to that node (ACL) — fix in the Tailscale admin console, not on the box. |
| Host key changed warning | Box was rebuilt/reimaged — verify that's expected before clearing the known_hosts line; a surprise key change is a red flag. |

On a NEW machine the fleet won't be reachable until: the machine has joined the tailnet AND the `~/.ssh/config` aliases exist. If either is missing, that's the first thing to fix (`agent-environment-setup` replicates the ssh config).

## The fleet inventory model

One folder per server, each with a README/IDENTITY doc; a top-level table is the map. Minimum columns that make a fleet operable:

| Column | Why it's load-bearing |
|---|---|
| Alias(es) | how you connect (`ssh <alias>`) |
| Address | tailnet IP / hostname |
| OS | shapes every command (apt vs dnf, systemd vs not) |
| Role | what it's FOR — routes the task |
| Status | on-role / degraded / empty / unreachable — never act blind on "degraded" |
| Capacity flag | high-RAM / high-load / near-full-disk → read-only without approval |

Read the fleet doc to ROUTE ("Elasticsearch work → the search box"), then verify that box live before touching it. If no fleet doc exists yet, build one with `server-identity-builder` before operating — you cannot safely run a fleet you haven't mapped.

## Per-box identity probe (run on connect, every session)

```sh
hostnamectl | grep -E 'hostname|Operating System|Machine ID'   # am I on the box I think I am?
uptime; free -h; df -h /                                        # load, RAM, disk — the capacity gate inputs
ss -tlnp 2>/dev/null | grep -vE '127\.0\.0\.1|\[::1\]' | head   # what's exposed beyond localhost
docker ps --format '{{.Names}}\t{{.Status}}' 2>/dev/null        # containers, if any
systemctl list-units --failed --no-pager 2>/dev/null            # anything already broken before you arrived
```

Match `Machine ID` / hostname against the fleet doc. Mismatch = you're on the wrong box or the doc is stale — STOP and reconcile (rebuild the doc) before any change.

## Fleet-wide read-only sweep (safe on all boxes)

To answer "what's the state of everything", loop the identity probe over aliases — read-only, capacity-flags respected, one box at a time so a hang is obvious:

```sh
for host in $(grep -iE '^host ' ~/.ssh/config | awk '{print $2}'); do
  echo "=== $host ==="
  ssh -o ConnectTimeout=8 -o BatchMode=yes "$host" \
    'hostnamectl --static; uptime | sed "s/.*load average/load/"; free -h | awk "/Mem:/{print \"RAM \" \$3 \"/\" \$2}"; df -h / | awk "NR==2{print \"disk \" \$5}"' \
    2>&1 | sed 's/^/  /'
done
```

A box that times out or errors is a finding — record it (`unreachable`), don't retry-loop it. Never put a state-changing command inside a fleet loop; a wrong flag then hits every box at once.

## Routing a task to the right box

1. Read the fleet doc's role column → candidate box(es).
2. Connect + identity-probe that box (confirm role matches reality — roles drift).
3. Check the capacity flag: high-RAM/high-load/near-full → observe only unless the user approved the change AND you re-verified headroom this session.
4. Hand the actual change to `server-ops-safety` (backup → one change → health-check → rollback line). Cross-box changes (move data A→B) = the change gate on EACH box, plus a `network-diagnosis` reachability check between them first.

## Done-gates

- **Fleet claim done** = every box in the claim was probed live this session (or explicitly marked unreachable with the error) — never reported from the fleet doc alone.
- **Fleet op done** = the target box was identity-confirmed, its capacity flag respected, and the change passed `server-ops-safety`'s done-gate on that box.
- **"Fleet healthy" is never said from memory** — it's the current sweep output or it isn't claimed.
