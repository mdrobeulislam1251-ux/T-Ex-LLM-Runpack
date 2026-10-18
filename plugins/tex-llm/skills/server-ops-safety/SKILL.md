---
name: server-ops-safety
description: Use before the first state-changing command in any task that touches a running machine or service — deploying, installing, restarting, deleting, pruning, editing service config, database DDL/DELETE, or anything invoking sudo or admin rights.
---

# Server Ops Safety

Every ops action runs against live state probed **this session** on **this machine** — never against remembered state, a previous session, or what "should" be running. The four gates below are ordered; a change that skips one is not done, it is a gamble.

## 1. Inventory First — Read Live State Before Any Change

Hard rule: **never install or start a second instance of something that may already be running — find it first.** A second Postgres, nginx, redis, or app process on the same box is the top cause of "worked yesterday" outages (port fights, split data dirs, two schedulers double-firing jobs).

POSIX (Linux/macOS — skip lines for tools not present, absence is itself a finding):

```sh
systemctl list-units --failed                       # anything already broken BEFORE you touch it
systemctl list-units --type=service --state=running --no-pager | tail -n +2 | head -40
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pm2 list 2>/dev/null                                # node process manager, if present
ss -tlnp                                            # every listener + owning PID (sudo for all PIDs)
df -h && df -i                                      # space AND inodes — both can be "full"
free -h
```

PowerShell (Windows):

```powershell
Get-Service | Where-Object Status -eq 'Running' | Sort-Object DisplayName | Select-Object -First 40
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
Get-NetTCPConnection -State Listen | Sort-Object LocalPort |
  Format-Table LocalAddress,LocalPort,OwningProcess -AutoSize
Get-CimInstance Win32_OperatingSystem |
  Select-Object @{n='FreeRAM_GB';e={[math]::Round($_.FreePhysicalMemory/1MB,1)}},
                @{n='TotalRAM_GB';e={[math]::Round($_.TotalVisibleMemorySize/1MB,1)}}
Get-PSDrive -PSProvider FileSystem | Select-Object Name,@{n='FreeGB';e={[math]::Round($_.Free/1GB,1)}}
```

Before installing/starting service X, all four probes, in order:

```sh
command -v X && X --version          # PowerShell: Get-Command X
systemctl status X 2>/dev/null       # PowerShell: Get-Service X*
docker ps -a --filter "name=X"       # it may live in a container, stopped counts too
ss -tlnp | grep :<its-default-port>  # PowerShell: Get-NetTCPConnection -LocalPort <port>
```

Any hit → reuse or explicitly decommission the existing instance first. All four empty → proceed.

When a running process is found, identify **which manager owns it** before touching it — stopping a process behind its manager's back just makes the manager restart it (or worse, mark it failed):

```sh
PID=<pid from ss/docker>
ps -o ppid=,comm= -p "$PID"; ps -o comm= -p "$(ps -o ppid= -p "$PID")"
# parent = systemd → systemctl owns it     → stop with: systemctl stop <svc>
# parent = containerd-shim/dockerd        → stop with: docker stop <ctr>
# parent = "PM2 vX" node process          → stop with: pm2 stop <name>
# parent = PID 1 but no unit, or a shell  → someone nohup'd it; report before killing
```

```powershell
$procId = <pid from Get-NetTCPConnection/docker>   # NOT $pid — $PID is read-only (the shell's own PID)
(Get-Process -Id $procId).Parent | Select-Object Id,ProcessName   # PowerShell 7+
Get-CimInstance Win32_Service | Where-Object ProcessId -eq $procId  # is it a Windows service?
```

Stop-and-report thresholds (before any change, not after):

- Any filesystem ≥ 90% used, or inodes ≥ 90% → resolve space first; changes on a near-full disk corrupt state.
- Free RAM < 300 MB and no swap → do not start anything new; the OOM killer picks victims, not you.
- `systemctl list-units --failed` non-empty → report the failed units before adding your change on top.

## 2. Destructive-Command Gate — Read-Only Twin First

Before any command that deletes, drops, prunes, or resets: run its **read-only twin**, show the impact (count + size + names), and only then execute. If the twin's output surprises you, the destructive command was about to surprise you harder.

| Destructive command | Read-only twin (run FIRST, show output) |
|---|---|
| `rm -rf <glob>` / `Remove-Item -Recurse` | `ls -la <same glob>` + `du -sh <same glob>` (PS: `Get-ChildItem <glob>` + measure) |
| `DELETE FROM t WHERE …` / `DROP TABLE t` | `SELECT count(*) FROM t WHERE <same WHERE>;` — the *identical* WHERE clause, copy-pasted |
| `docker system prune -a` | `docker system df` + `docker ps -a --filter status=exited` + `docker images -f dangling=true` |
| `docker rm` / `docker rmi` / `docker volume rm` | `docker inspect <name>` — check Mounts; a volume rm can be user data |
| `git reset --hard` / `git checkout -- .` | `git status` + `git stash list` + `git diff --stat` — uncommitted work is unrecoverable |
| `apt purge` / `winget uninstall` | `apt-cache rdepends --installed <pkg>` — what else depends on it |
| truncating a "huge log" | `du -sh <file>` + `lsof <file>` — if a process holds it open, truncate frees nothing until restart |

Irreversible actions — data deletion, DROP anything, volume removal, purging packages with data dirs, `git push --force` — additionally require an **explicit go from the user in this conversation, after seeing the impact output**. "Clean it up" issued before the impact was known does not count as the go.

Pass criteria for this gate: twin output shown, row/file count and size stated in one line ("deletes 3 containers, 2 volumes (1.4 GB), 0 named volumes with data"), go received where required. Fail any of these → the destructive command does not run.

## 3. Change Protocol — Backup, One Change, Health-Check, Rollback Line

**Write the rollback line BEFORE the change**, in the form: `rollback = restore <backup artifact> + restart <service>`. If you cannot complete that sentence, you do not understand the change well enough to make it.

Backup exactly what the change touches, with a timestamp suffix:

```sh
# single config file (preserves perms/ownership)
cp -a "$FILE" "$FILE.bak-$(date +%Y%m%d-%H%M%S)"
# whole config directory (locate it first: systemctl cat <svc> | grep -E 'ExecStart|EnvironmentFile')
tar -czf "cfgbackup-$(date +%Y%m%d-%H%M%S).tar.gz" -C "$(dirname "$CONF_DIR")" "$(basename "$CONF_DIR")"
# database before schema/data changes (custom format → selective restore with pg_restore)
pg_dump -Fc -f "db-$(date +%Y%m%d-%H%M%S).dump" "$DB_NAME"
```

```powershell
Copy-Item $file "$file.bak-$(Get-Date -Format yyyyMMdd-HHmmss)"
Compress-Archive -Path $confDir -DestinationPath "cfgbackup-$(Get-Date -Format yyyyMMdd-HHmmss).zip"
```

A backup that was never read back is a hope, not a backup — verify it in one command before proceeding:

```sh
tar -tzf cfgbackup-*.tar.gz | head    # archive lists its members = readable
pg_restore --list db-*.dump | head    # dump parses = restorable
```

Then the loop — **one change at a time**, never batched:

1. Apply exactly one change (one file edit, one package, one flag).
2. Validate config before restart where the tool supports it: `nginx -t`, `sshd -t`, `apachectl configtest`, `caddy validate`, `docker compose config -q`, `pg_ctl … --check` equivalents. A failed validate = fix or roll back, do not restart.
3. Restart/reload the one affected service (`reload` over `restart` when supported — no dropped connections).
4. Health-check within 60 seconds:

```sh
systemctl is-active <svc>                     # expect: active   (PS: (Get-Service <svc>).Status → Running)
curl -fsS -m 5 http://127.0.0.1:<port>/health # expect: HTTP 200; -f makes non-2xx exit non-zero
```

   Plus one service-specific smoke: `psql -c 'SELECT 1'`, `redis-cli ping` → `PONG`, `docker inspect --format '{{.State.Health.Status}}' <ctr>` → `healthy`, or one real request that exercises the change.
5. Health-check fails → execute the pre-written rollback line **immediately**, verify health again, then diagnose. Never stack a second change on top of a failing first one.

Pass criteria: backup exists (verified with `ls -la` / `Test-Path`), rollback line written before step 1, health-check output shown after each change. "Restarted it and it's probably fine" fails this gate.

## 4. Error Table — Symptom → Diagnosis → Fix

| Verbatim symptom | Diagnose | Fix |
|---|---|---|
| `bind: address already in use` / `EADDRINUSE` / `Only one usage of each socket address … is normally permitted` | POSIX: `ss -tlnp 'sport = :<port>'` or `sudo fuser <port>/tcp`. PS: `Get-Process -Id (Get-NetTCPConnection -LocalPort <port>).OwningProcess` | Never `kill -9` blind: identify the holder. Same app already running → use it (Gate 1). Stale/other process → stop it via its own manager (systemctl/docker/pm2), not raw kill, or move your port. |
| Service starts, then dies within seconds; `systemctl status` shows `activating (auto-restart)` or `Active: failed (Result: exit-code)` | `journalctl -u <svc> -n 50 --no-pager` — the real error is in the last lines **before** `Main process exited, code=exited, status=N`. Windows: `Get-WinEvent -LogName Application -MaxEvents 50` | Common culprits in that log tail: missing env var/EnvironmentFile, unreadable config path, port conflict (see row above), wrong `User=` lacking permission on its data dir. Fix the logged cause; do not loop restarts. |
| Disk-full in disguise — no message says "disk": Postgres `could not write to file … No space left on device` or `PANIC: could not write to file "pg_wal/…"`; `docker pull` dies with `failed to register layer`; SQLite `database or disk is full`; app writes silently truncated | `df -h` **and** `df -i` — inode exhaustion shows 100% inodes with free space; also `docker system df` for image/layer bloat | Free space *before* restarting anything (a DB restarting on a full disk can corrupt WAL). Biggest offenders: `du -xh --max-depth=2 <mount> \| sort -rh \| head -20`, old journal logs (`journalctl --vacuum-size=200M`), dangling docker layers (Gate 2 twin first). |
| `Job for <svc>.service failed because the control process exited with error code` | `systemctl status <svc>` shows the summary; full story via the journalctl command above | Same fix path as starts-then-dies; if config was just edited, run the validator (Gate 3 step 2) — a typo is the usual cause. |
| Container `Restarting (1) X seconds ago` loop | `docker logs --tail 50 <ctr>` | Same class as starts-then-dies: read the last lines before exit; check env vars and volume mount paths exist on the host. |
| `Permission denied` binding a port < 1024 as non-root (`listen tcp :443: bind: permission denied`) | confirm with `id -u` (non-zero) and the port number | Do not run the app as root for this. Either `sudo setcap 'cap_net_bind_service=+ep' <binary>`, or bind a high port (8080/8443) and let the reverse proxy own 80/443 — the Gate 5 pattern. |
| `curl: (7) Failed to connect … Connection refused` immediately after a deploy that "succeeded" | `ss -tlnp \| grep <port>` (PS: `Get-NetTCPConnection -LocalPort <port>`) — is anything listening at all, and on which address? | Nothing listening → the service died post-start (see starts-then-dies row). Listening on `127.0.0.1` while you curl the external IP (or vice versa) → address mismatch, not an outage; fix the probe or the bind, per Gate 5. |
| `Failed to start <svc>.service: Unit <svc>.service is masked.` | `systemctl list-unit-files \| grep <svc>` shows `masked` | Someone deliberately disabled it — find out why before `systemctl unmask <svc> && systemctl start <svc>`; masking is usually a breadcrumb from a past incident. |

## 5. Bind Rule — Never 0.0.0.0 for Internal Services

Databases, caches, queues, admin panels, metrics endpoints, and internal APIs bind to `127.0.0.1` (or a private interface) — **never** `0.0.0.0` "to make it reachable". Exposure to the network goes through exactly one deliberate front door: a reverse proxy (nginx/Caddy/Traefik) with TLS and auth, an SSH tunnel (`ssh -L <localport>:127.0.0.1:<svcport> <host>`), or a private overlay/mesh VPN — whichever the environment already uses (probe, don't pick).

Audit for accidental exposure (run during Gate 1 on any box you operate):

```sh
ss -tlnp | awk '$4 ~ /0\.0\.0\.0|\[::\]/'          # every service listening on all interfaces
```

```powershell
Get-NetTCPConnection -State Listen |
  Where-Object { $_.LocalAddress -in '0.0.0.0','::' } |
  Format-Table LocalAddress,LocalPort,OwningProcess -AutoSize
```

Each hit is either (a) the deliberate front door — fine, or (b) reported to the user in one line with the bind-to-localhost fix for that service (`listen_addresses = 'localhost'` in postgresql.conf, `bind 127.0.0.1` in redis.conf, `-p 127.0.0.1:8080:8080` instead of `-p 8080:8080` in docker). Docker note: a plain `-p 8080:8080` publishes on all interfaces **and bypasses ufw/firewalld rules** — always write the `127.0.0.1:` prefix for internal containers.

## Done-Gate

An ops change is done only when ALL hold: (1) inventory was probed this session, (2) destructive steps showed their read-only twin and impact first, (3) a timestamped backup exists and the rollback line was written before the change, (4) the post-change health-check output is shown and passing, (5) no internal service is newly listening on `0.0.0.0`. Anything less is reported as "changed, not verified" — never as done.
