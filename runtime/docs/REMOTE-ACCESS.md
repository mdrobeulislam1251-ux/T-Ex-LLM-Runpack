# Remote access to the T-ex LLM web UI

After setup, the server listens on **`HOST_PORT`** (default **3006**) on **`HOST_BIND`** (default `0.0.0.0`).

Choose one access pattern. Prefer private networks for demos; put TLS in front for public domains.

---

## 1. Local only

```text
http://127.0.0.1:3006/
```

No firewall changes. Best for development.

---

## 2. Same LAN (private IP)

1. Find the machine IP:
   - **macOS:** System Settings → Network, or `ipconfig getifaddr en0`
   - **Linux:** `hostname -I` or `ip -4 addr`
   - **Windows:** `ipconfig`
2. Ensure the host allows the port:
   - Linux `ufw`: `sudo ufw allow 3006/tcp`
   - Windows Defender Firewall: allow inbound TCP for your chosen port
   - macOS: allow incoming for Python if prompted
3. Open from another device:

```text
http://192.168.x.x:3006/
```

Replace with your private IP and port.

Set a real API key if the service is reachable by others:

```bash
# .env
HOST_API_KEY=long-random-secret
```

---

## 3. Tailscale (recommended private mesh)

1. Install Tailscale on the **server** and client devices: https://tailscale.com/download  
2. `tailscale up` and sign in.  
3. Note the MagicDNS name or Tailscale IP (`100.x.y.z`):
   ```bash
   tailscale status
   tailscale ip -4
   ```
4. Keep T-ex bound to all interfaces (default):
   ```env
   HOST_BIND=0.0.0.0
   HOST_PORT=3006
   ```
5. From any device on the same tailnet:

```text
http://100.x.y.z:3006/
# or
http://your-machine.tailnet-name.ts.net:3006/
```

### Tailscale SSH (ops shell, not the web UI)

Optional admin path:

```bash
# enable per Tailscale docs
ssh your-machine.tailnet-name.ts.net
```

Store the hostname in the web console **Settings** for operator reference.

---

## 4. Public domain (DNS A record)

### DNS

Create an **A** record:

| Type | Name | Value |
|------|------|--------|
| A | `tex` (or `@`) | Your server public IPv4 |

Example: `tex.example.com` → `203.0.113.10`

Propagation can take minutes to hours. Check:

```bash
dig +short tex.example.com A
```

### TLS reverse proxy (example: Caddy)

Do **not** expose plain HTTP on the public internet without TLS and a strong `HOST_API_KEY`.

`Caddyfile`:

```caddy
tex.example.com {
    reverse_proxy 127.0.0.1:3006
}
```

Or **nginx**:

```nginx
server {
    listen 443 ssl http2;
    server_name tex.example.com;

    # ssl_certificate ...;
    # ssl_certificate_key ...;

    location / {
        proxy_pass http://127.0.0.1:3006;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Run T-ex only on localhost if the proxy is local:

```env
HOST_BIND=127.0.0.1
HOST_PORT=3006
HOST_API_KEY=use-a-long-random-secret
```

---

## 5. Port selection recap

| Goal | Setting |
|------|---------|
| Default product port | `3006` |
| Customer choice at install | `bash scripts/setup.sh --port 8088` |
| One-off | `texllm serve --port 4000` |
| Persist | `HOST_PORT=4000` in `.env` |

---

## Security checklist

- [ ] Change `HOST_API_KEY` away from `change-me` on shared networks  
- [ ] Prefer Tailscale or VPN over raw public ports  
- [ ] Use HTTPS for public DNS names  
- [ ] Disable local CLI spawn on untrusted multi-tenant hosts: `ALLOW_LOCAL_CLI=false`  
- [ ] Treat CLI spawn as **code execution** with the rights of the host OS user  
