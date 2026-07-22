---
name: server-identity-builder
description: Use to build or refresh a server's identity document from a live read-only sweep — hostname, access model, network, capacity, data stores, containers, services, ingress/tunnels, listening ports, firewall, and cautions — writing a portable doc that records secret PATHS only, never values. Feeds the fleet inventory used by server-fleet-management.
---

# Server Identity Builder

An identity doc is a server's verified passport: what it is, how you reach it, what it holds, and what will hurt you. Built ONLY from a live read-only sweep and dated — an undated or hand-guessed identity doc is worse than none, because it's trusted.

## Rules

- **Read-only.** Every command here observes; none changes state. Building an identity doc must never restart, install, or write on the box.
- **Secrets = paths only.** When you find `secret.env` / a keystore / a password file: record its PATH and mode (`ls -l` shows `-rw------- root root`), never its contents. `grep`-ing a secret into the doc is the one unforgivable error.
- **Date + method every doc.** Header: capture date, "read-only over <access method>", and a "verify before acting — state drifts" line.
- **Portable output.** The doc holds this box's real facts (that's its job). The SKILL and any templates you generate stay free of hardcoded fleet specifics.

## The sweep (run top to bottom, paste real output into the doc)

```sh
# 1. Identity
hostnamectl                                   # static hostname, OS, kernel, chassis, Machine ID
cat /etc/os-release | grep PRETTY_NAME

# 2. Access — how you got in (record the model, not credentials)
tailscale status 2>/dev/null | head -3        # if tailnet: this node's name + IP
who am i; id                                  # which user you connected as
ss -tlnp 2>/dev/null | awk '$4 ~ /:22$/'      # which interface sshd binds

# 3. Network
ip -brief addr | grep -v ' lo '               # every interface + address (tailscale0/eth/docker)
ip route | grep default

# 4. Capacity
nproc; free -h; swapon --show
df -h --output=target,size,used,pcent,iavail / /var /data 2>/dev/null

# 5. Data stores — engines + BIND address (localhost vs exposed matters)
ss -tlnp 2>/dev/null | grep -iE ':(5432|5433|3306|6379|9200|9300|8123|27017|9000)'
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Ports}}' 2>/dev/null

# 6. Services & process managers
systemctl list-units --type=service --state=running --no-pager | tail -n +2 | head -40
pm2 list 2>/dev/null; supervisorctl status 2>/dev/null

# 7. Ingress / tunnels (how the outside reaches in)
ls /etc/cloudflared/ 2>/dev/null; systemctl list-units 'cloudflared*' 'newt*' 'tailscale*' --no-pager 2>/dev/null
nginx -T 2>/dev/null | grep -E 'server_name|listen' | head -40    # if nginx present
caddy list-modules >/dev/null 2>&1 && cat /etc/caddy/Caddyfile 2>/dev/null | grep -E '^\S+ \{|reverse_proxy'

# 8. Listening ports (the full map)
ss -tlnp 2>/dev/null | awk 'NR>1{print $4, $1}' | sort -u

# 9. Firewall (real enforcing state, not just "is ufw installed")
ufw status verbose 2>/dev/null; iptables -S INPUT 2>/dev/null | head

# 10. Secret files — PATHS + modes only, NEVER contents
find /data/secrets /etc /root /opt -maxdepth 3 -type f \( -name '*.env' -o -name '*secret*' -o -name '*password*' \) -printf '%M %p\n' 2>/dev/null
```

## Document template (fill from the sweep above)

```markdown
# <alias> — Server Identity & Config
_Live snapshot <DATE>, read-only over <access method>. Verify before acting — state drifts._

## 1. Identity      | hostname, OS, Machine ID, fleet role, aliases
## 2. Access (SSH)  | model (Tailscale/key/bastion), which user, connect gotchas, sshd bind
## 3. Network       | interfaces + addresses (tailnet/public/private/docker), default route
## 4. Capacity      | vCPU, RAM (total/used/avail), swap, disk (used%/free); CAPACITY FLAG if tight
## 5. Data stores   | engine, bind address, port, role, secret-file PATH (value not read)
## 6. Containers    | name, image, published ports
## 7. Services      | key running systemd/pm2/supervisor units
## 8. Ingress       | cloudflared/newt tunnels + nginx/caddy server_names -> local service
## 9. Listening ports| bind:port -> service (flag every 0.0.0.0 as "exposed")
## 10. Firewall     | real enforcing state (ufw active? iptables INPUT policy?)
## 11. Cautions     | capacity history, frozen/backup stores, "don't lock inbound because X"
```

## Deriving the facts that actually matter

- **Capacity flag**: set it when RAM used > ~70%, load > vCPU count, OR any filesystem > 80%. This flag is what `server-fleet-management` reads to decide observe-only.
- **Exposed services**: any store/admin panel on `0.0.0.0` or a public interface goes in Cautions — cross-reference `server-ops-safety` Bind Rule.
- **Ingress dependency**: note when public sites depend on a public-443 origin vs an outbound tunnel — locking inbound to the tailnet would take origin-based sites offline. This single caution prevents a class of self-inflicted outages.
- **Frozen/backup stores**: mark any store that is a cold backup so no one treats it as live.

## Refreshing an existing doc

Re-run the sweep, DIFF against the current doc, and update only what changed — noting the re-verify date and what drifted ("containers, memory, firewall confirmed unchanged; added new port 4600"). Never silently overwrite a dated snapshot; the history of what changed is itself diagnostic.

## Done-gates

- **Identity doc done** = every section filled from THIS session's sweep output, dated, secret files listed by path+mode only, capacity flag decided, exposed-port cautions written.
- **Fleet map done** = one row per box (alias, address, OS, role, status, capacity flag), each row backed by a per-box identity doc built by this skill.
- A doc with any field guessed rather than probed is marked `UNVERIFIED: <field>` — never presented as confirmed.
