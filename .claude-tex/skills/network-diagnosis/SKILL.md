---
name: network-diagnosis
description: Use when a host or service cannot be reached or fails in transit — "can't connect", DNS resolve errors, TLS/certificate failures, 502/503/504 behind a proxy, or a VPN/overlay/tunnel path misbehaving — to walk the symptom down the layers with exact probes to a named guilty component.
---

# Network Diagnosis — Symptom → Layer → Command → Verdict

Connectivity failures are layered: DNS ≠ unreachable ≠ cert ≠ app-down. Fixing the wrong layer wastes an hour and often makes it worse. This tree probes one layer at a time, in order, and stops at the first failing one. Never fix a layer above the broken one.

## Rule Zero — read the client's error before probing

The error the user pasted usually names the layer already. Route on it:

| Client error (verbatim fragment) | Start at |
|---|---|
| `Could not resolve host` / `getaddrinfo ENOTFOUND` / `Name or service not known` / `No such host is known` | Layer 1 — DNS |
| `Connection refused` / `Connection timed out` / `No route to host` / `Unable to connect` | Layer 2 — TCP |
| anything containing `SSL`, `TLS`, `certificate`, `handshake` | Layer 3 — TLS |
| any HTTP status code was received (4xx/5xx) | Layer 4 — HTTP (layers 1–3 are proven working) |
| works on one address/path but not another | Layer 5 — split test, then Layer 6 if an overlay/tunnel is involved |

Probe your toolset first — never assume what's installed:

```sh
# POSIX
command -v dig nslookup curl nc openssl ss ip 2>/dev/null
```
```powershell
# PowerShell — note: bare `curl` is an alias for Invoke-WebRequest; ALWAYS call curl.exe
Get-Command Resolve-DnsName, Test-NetConnection, curl.exe, openssl -ErrorAction SilentlyContinue | Select-Object Name, Source
```

## Layer 1 — Name resolution

```sh
dig +short <name>            # answer only; empty output needs the full query to interpret:
dig <name>                   # read "status:" and "ANSWER:" in the header
nslookup <name>              # fallback when dig is absent
```
```powershell
Resolve-DnsName <name> -Type A
```

| Probe output | Verdict | Fix |
|---|---|---|
| `status: NXDOMAIN` / nslookup `Non-existent domain` / `DNS name does not exist` | Name does not exist at this resolver | Typo in the name; record never created — add A/AAAA/CNAME at the authoritative zone; or it's an internal-only name being asked of a public resolver (split-horizon) — use the internal resolver or the overlay's DNS |
| `status: NOERROR` but `ANSWER: 0` (`dig +short` prints nothing) | Name exists, no record of the queried type | Zone has only CNAME/AAAA/TXT for it — query the right type (`dig <name> AAAA`, `dig <name> CNAME`) or add the missing A record |
| Resolves, but to an IP you don't expect | Stale cache or wrong record | Compare against authoritative: `dig +short <name> @$(dig +short NS <zone> \| head -1)`. If authoritative is right, flush local cache: `resolvectl flush-caches` (Linux) / `Clear-DnsClientCache` (Windows). Also check hosts-file overrides: `grep -i <name> /etc/hosts` / `Select-String <name> "$env:SystemRoot\System32\drivers\etc\hosts"` |
| Correct IP returned | DNS is innocent | Go to Layer 2 |

Cross-resolver check when results look suspicious: `dig +short <name> @1.1.1.1` vs the default resolver. Different answers = split-horizon DNS or a stale resolver, not a server problem.

## Layer 2 — TCP reachability

Ping first, but read it correctly: **ICMP is routinely blocked — ping failure proves nothing.** Ping success only proves L3 routing; it says nothing about your port. Never report "host is down" on ping evidence alone.

The real probe is TCP to the actual port:

```sh
curl -sv --connect-timeout 5 telnet://<host>:<port> </dev/null    # any TCP port, not just HTTP
nc -vz -w 5 <host> <port>                                          # alternative if nc exists
```
```powershell
Test-NetConnection <host> -Port <port>    # read TcpTestSucceeded, not just PingSucceeded
```

Decision rule — the failure's **timing** is the diagnosis:

| Result | Timing | Verdict | Next action |
|---|---|---|---|
| `Connection refused` | Instant (< 1 s) | Host is UP; nothing listening on that port | On the server: `ss -tlnp \| grep :<port>` (Linux) / `Get-NetTCPConnection -State Listen -LocalPort <port>` (Windows). No line = service not running — start it, check its logs. Line shows `127.0.0.1:<port>` = bound to loopback only, unreachable from outside by design — change bind address deliberately, or front it with a proxy |
| Timeout | Only after the full timeout elapses | Packet silently dropped: firewall (host or cloud security group), no route, or wrong IP from Layer 1 | Check host firewall (`nft list ruleset` / `ufw status` / `Get-NetFirewallProfile`), then the cloud/provider firewall for that port, then routing (`ip route get <ip>` / `Find-NetRoute -RemoteIPAddress <ip>`) |
| `Connection reset by peer` | Usually instant or mid-handshake | Something accepted, then killed it: middlebox/IDS, a proxy that dislikes the traffic, speaking TLS to a plaintext port (or vice versa), or the service crashing on accept | Retry with/without TLS; probe from a different vantage (Layer 5); read the service's logs at the exact timestamp |
| Success | — | L1–L2 healthy | Plain TCP service: done here. TLS/HTTP service: go to Layer 3 |

## Layer 3 — TLS

Always pass SNI — without `-servername`, multi-tenant servers return their default cert and you will misdiagnose a healthy site:

```sh
openssl s_client -connect <host>:<port> -servername <name> </dev/null 2>&1 | grep -E "verify|subject=|issuer=|expire"
echo | openssl s_client -connect <host>:<port> -servername <name> 2>/dev/null | openssl x509 -noout -dates -subject -issuer
curl -vI https://<name>/ 2>&1 | grep -E "subject:|issuer:|expire date:|SSL"
```
On Windows use `curl.exe` for the same lines; if openssl is absent: `winget install ShiningLight.OpenSSL.Light` or read the cert via `curl.exe -vI`.

The three classic failures, verbatim, with fixes:

| Verbatim output | Verdict | Fix |
|---|---|---|
| `verify error:num=10:certificate has expired` / curl: `SSL certificate problem: certificate has expired` | Cert past `notAfter` | Renew it. If renewal already ran but the error persists, the service is still serving the old file from memory — reload/restart the server process, then re-probe |
| `verify error:num=62:hostname mismatch` / curl: `no alternative certificate subject name matches target hostname '<name>'` | Cert issued for a different name — SAN doesn't cover this hostname | Reissue with the right SAN, or fix vhost/SNI routing so the correct cert is served for this name. Confirm what was actually served with the `subject=`/SAN output above |
| `verify error:num=20:unable to get local issuer certificate` | Incomplete chain — server sends leaf only, no intermediates | Serve the full chain (leaf + intermediates — e.g. `fullchain.pem`, not `cert.pem`, in the server config). Signature symptom: "works in the browser, fails in curl/CLI" — browsers fetch or cache intermediates; CLIs don't |
| `verify error:num=18:self-signed certificate` | Self-signed or private CA not in the client's trust store | Expected internally: distribute the CA to clients or pin it (`curl --cacert`). On a public endpoint: wrong cert deployed |

Verify pass = `Verify return code: 0 (ok)`. Anything else is a Layer 3 fail — do not proceed to blaming the app.

## Layer 4 — HTTP (behind a proxy/LB/CDN, which is almost always)

```sh
curl -sv -o /dev/null https://<name>/<path>        # status + all response headers
```
```powershell
curl.exe -sv -o NUL https://<name>/<path>
```

5xx triage — each code names a different broken hop:

| Status | Meaning | Guilty hop | Probe |
|---|---|---|---|
| `502 Bad Gateway` | Proxy reached for the upstream and got refused/garbage | Upstream (app) down, or proxy config points at the wrong upstream host:port | From the proxy host, run the Layer 2 probe against the configured upstream address |
| `503 Service Unavailable` | No healthy backend in the pool (health checks failing) or deliberate maintenance/overload shed | Backends failing their health check, or pool empty | Hit the health-check path directly on a backend; check the LB's backend-pool status |
| `504 Gateway Timeout` | Upstream accepted the connection but didn't answer within the proxy's timeout | Slow app — usually a dead/slow dependency behind it (DB, downstream API), or a drop between proxy and app | Time the app directly: `curl -s -o /dev/null -w "%{time_total}\n" <upstream-url>` from the proxy host; compare against the proxy's timeout setting |
| `500` from the app itself | Request traversed everything; the app crashed handling it | The application | App logs — this is a code bug, not a network problem. Stop network diagnosis |

Identify **which tier generated the error page** from response headers: the `Server:` header on the error response names the tier that wrote it (nginx/envoy/cloud-LB banner vs the app's framework), and proxy/CDN markers (`Via:`, `X-Served-By:`, vendor request-id headers) show which hops the request cleared. Decision rule: every hop **before** the tier that generated the error is proven working; the guilty component is that tier's upstream.

## Layer 5 — The split test (locates the failing hop in ≤3 probes)

Run the same probe (Layer 2 or 4, whichever failed) from three vantage points:

- **A — on the serving host itself**: `curl -sv http://127.0.0.1:<port>/` (use the actual bind address from `ss -tlnp`)
- **B — from another host on the same network/overlay**: same probe against the host's internal/overlay IP
- **C — from outside**: same probe against the public name/IP

| A (local) | B (inside) | C (outside) | Guilty component |
|---|---|---|---|
| FAIL | — | — | The service itself: not running, wrong port, or crashed. Fix the service; skip all network theories |
| PASS | FAIL | — | Host-level: bound to `127.0.0.1` only, or host firewall blocking the port. `ss -tlnp` + firewall rules |
| PASS | PASS | FAIL | Edge only: public DNS record, LB/proxy/CDN config, cloud firewall/NAT, or the tunnel (→ Layer 6) |

A fails ⇒ B and C are noise. Always run A first — it's the cheapest and eliminates the most.

## Layer 6 — Overlay / tunnel branch

Applies when traffic rides a mesh VPN/overlay network (WireGuard-class, corporate VPN) or a reverse tunnel to an edge provider. Core discipline: **test the underlay and the overlay separately** — identical failure on both means the overlay is innocent.

| Symptom | Verdict | Probe / fix |
|---|---|---|
| Works on public/LAN IP, fails on the overlay IP | Overlay layer guilty: daemon down, peer unauthenticated/expired key, or overlay ACL denying that port | Check the overlay daemon's own status CLI on BOTH ends first; then Layer 2 probe to the overlay IP. Auth/key state and ACL rules live in the overlay's control plane, not the OS firewall |
| Overlay hostname fails but the overlay IP works | Overlay's DNS layer, not its data path | The overlay's name service is a separate component from packet forwarding — fix its resolver config/registration; don't touch routes |
| Tunnel shows "connected/healthy" at the provider, but requests return 502 from the edge | Tunnel is fine; the **origin service behind it** is down, or the tunnel config points at the wrong origin host:port | On the tunnel host, Layer 2 probe the exact origin URL from the tunnel's config file. A healthy tunnel faithfully delivers requests to a dead origin |
| Small requests succeed over the overlay, large transfers hang mid-stream | MTU/fragmentation on the tunnel path — encapsulation overhead shrinks the effective MTU | Probe the path MTU: `ping -M do -s 1400 <overlay-ip>` (Linux; raise/lower `-s` to find the ceiling) / `ping -f -l 1400 <overlay-ip>` (Windows). `Frag needed` or silence above a size = confirmed. Fix: lower the tunnel interface MTU below the ceiling, or clamp TCP MSS on the tunnel interface |
| Fails identically on overlay AND public path | Not the overlay | Go back to Layers 1–4 on the service itself |

## Last resort — watch the wire

Only when the layer probes contradict each other (e.g. service listening, firewall open, yet timeouts). Capture the handshake itself:

```sh
# On the SERVER, while re-running the failing probe from the client:
tcpdump -ni any "tcp port <port>" -c 20
```
```powershell
# Windows server equivalent (built in):
pktmon filter add -p <port>; pktmon start --etw -m real-time
# stop with: pktmon stop; pktmon filter remove
```

Read the capture with three rules:

- Client's `SYN` never appears in the server capture → dropped **before** the host: upstream firewall, routing, NAT, or the probe went to a different IP than you think (re-check Layer 1).
- `SYN` arrives, no `SYN-ACK` leaves → the host itself: local firewall INPUT drop, or listener on a different address/port than assumed (`ss -tlnp` again, trust the capture over the config).
- `SYN-ACK` leaves but the client never sees it → asymmetric routing or return-path NAT — the reply is exiting a different interface than the request entered.

## Done-gate

A diagnosis is DONE only when all three hold:

1. **Named**: one guilty layer + component ("nginx serves leaf-only chain", not "TLS issue").
2. **Proven**: a verbatim probe output in the report that demonstrates it.
3. **Re-probed**: after the fix, the ORIGINAL failing probe was re-run and now passes — its output included.

"Restarted it and it seems fine" without the passing re-probe = not done. A fix that skipped layers ("rebooted the box") without identifying the layer = not a diagnosis, report it as such.
