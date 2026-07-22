---
name: server-fleet
description: Use for multi-server SSH fleet management — building and maintaining per-server identity cards (the identity builder), Tailscale/key-based SSH access doctrine, fleet-wide health sweeps, and the safety rails for production boxes. The registry format works for any fleet; server facts are probed live, never assumed.
---

# Server Fleet — Management & Identity Builder

One identity card per server, built from live probes, dated, and treated as binding documentation. The fleet is managed through SSH config aliases so every command stays portable across machines.

## The registry convention

```
servers/
  README.md                # fleet-at-a-glance table: alias | IP | OS | role | status | doc
  <alias>/IDENTITY.md      # one card per server (template below)
```

Status legend: ✅ on-role · ⚠️ attention (say why: RAM, load, legacy) · 🕳️ provisioned-but-empty · ❌ unreachable.

### Identity card template (per server)

```markdown
# <alias> — <role, one line>
_Snapshot <date> — read-only probe. Verify before acting; state drifts._

## Identity
| alias / other names | OS | chassis | machine-id |
## Access
- Method: tailscale-ssh | key-ssh (via ~/.ssh/config alias `<alias>`)
- User: <user> (flag root-only boxes explicitly — wrong-user is the #1 login failure)
## Network
| interface | address |   (tailnet, public, private — note which routes actually work)
## Capacity
| vCPU | RAM (total/used) | disk (total/used/free) |
## Services
- containers (docker ps), systemd units, listening ports (ss -tlnp) — bind address matters: 127.0.0.1 vs tailnet vs 0.0.0.0
## Data it holds
- what irreplaceable data lives here, sizes, which store
## Cautions  ← BINDING for every agent
- e.g. "high RAM history — no new installs", "production data — read/observe only", "cold backup — never treat as live"
```

Secrets rule (hard): identity cards record env-file PATHS and secret NAMES only. Never read or print secret file contents into a card. Never put passwords in cards, commands, or ssh configs.

## The identity builder (scan → probe → card)

**1. Discover candidates** — union of:

```sh
# POSIX — aliases from ssh config
grep -iE '^Host ' ~/.ssh/config | tr ' ' '\n' | grep -v -i '^host$' | grep -v '[*?]'
tailscale status 2>/dev/null   # tailnet peers (name + 100.x.x.x + online state)
```
```powershell
# PowerShell
Select-String -Path "$env:USERPROFILE\.ssh\config" -Pattern '^Host\s+(.+)' | ForEach-Object { $_.Matches[0].Groups[1].Value -split '\s+' } | Where-Object { $_ -notmatch '[*?]' }
tailscale status
```

**2. Probe each candidate** — read-only, non-interactive, time-boxed:

```sh
ssh -o BatchMode=yes -o ConnectTimeout=8 <alias>