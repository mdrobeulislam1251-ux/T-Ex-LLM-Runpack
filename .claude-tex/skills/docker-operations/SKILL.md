---
name: docker-operations
description: Use for any container task — writing Dockerfiles, compose stacks, containers that exit or restart-loop, container networking and DNS, volume/permission errors, registry auth, or disk cleanup — engine and compose facts probed at runtime.
---

# Docker Operations

Containers fail in a small number of famous ways. Probe the engine, read the exit code, walk the ladder — don't guess.

## Probe

```sh
docker version --format '{{.Server.Version}}'   # errors here = daemon problem, not your container
docker compose version                          # v2 plugin; if missing, try legacy: docker-compose --version
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

| Verbatim output | Fix |
|---|---|
| `Cannot connect to the Docker daemon at ... Is the docker daemon running?` | Engine down: start Docker Desktop (Win/mac; check WSL2: `wsl -l -v`), `systemctl status docker` on Linux. Also check `docker context ls` — you may be pointed at a dead remote context |
| `docker: 'compose' is not a docker command` | Only legacy v1 installed — use `docker-compose` (hyphen) or install the compose plugin; syntax below is v2 |
| `permission denied ... /var/run/docker.sock` | Linux: user not in `docker` group — `sudo usermod -aG docker $USER` + re-login |

## Dockerfile doctrine

- **Multi-stage always**: build stage holds the toolchain, final stage `FROM` a slim runtime, `COPY --from=build` only artifacts.
- **Cache order is the build-speed lever**: copy manifests + install deps BEFORE copying source:

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY --from=build /app/dist ./dist
USER node
EXPOSE 3000
CMD ["node", "dist/server.js"]
```

- `.dockerignore` is mandatory: `node_modules`, `.git`, `.env*`, `dist` — without it you bake secrets into layers and bust the cache on every commit.
- Run as non-root (`USER node` / a created user) — root-in-container is a finding in any security review.
- Numeric: a Node/Python API image on a slim base should land **< 400MB**; ≥ 1GB means the toolchain or dev deps leaked into the final stage — inspect with `docker history <image>`.

## Compose doctrine

The app-starts-before-db race is solved with healthchecks, not sleeps:

```yaml
services:
  db:
    image: postgres:16
    env_file: .env
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres}"]
      interval: 5s
      timeout: 3s
      retries: 10
  api:
    build: .
    env_file: .env
    ports:
      - "3000:3000"
    depends_on:
      db:
        condition: service_healthy
volumes:
  pgdata:
```

- Named volumes for data, bind mounts for source in dev only.
- Secrets via `env_file:` — never literal values under `environment:` in a committed file.
- `docker compose config` renders the final merged file — run it when env interpolation misbehaves.

## Debug ladder (90 seconds, in order)

1. `docker compose ps` / `docker ps -a` — state + exit code
2. `docker logs --tail 100 <c>` — the answer is here 80% of the time
3. `docker inspect --format '{{.State.ExitCode}} {{.State.OOMKilled}} {{.RestartCount}}' <c>`
4. `docker exec -it <c> sh` — then `env | sort`, is the file/port/env actually there?
5. `docker events --since 10m` — restart loops and OOM kills you didn't see

| Exit code | Meaning → action |
|---|---|
| `137` | SIGKILL — OOM if `OOMKilled=true` (raise memory limit or fix the leak), else forced stop |
| `126` | Entrypoint exists but not executable — `chmod +x` in the image |
| `127` | Entrypoint/command not found. On Windows repos this is usually **CRLF**: `#!/bin/sh\r` → verbatim `no such file or directory` for a file that exists. Fix: `.gitattributes` → `*.sh text eol=lf`, re-checkout |
| `1` | App error — back to step 2, read the logs |

## Networking

- Same compose network: containers reach each other by **service name + internal port** (`db:5432`). `localhost` inside a container is that container — the #1 config error: `DATABASE_URL` host must be `db`, not `localhost`, when the API runs in compose.
- From the host: only published ports (`ports:`). Container → host service: `host.docker.internal` (Desktop; on Linux add `extra_hosts: ["host.docker.internal:host-gateway"]`).
- DNS check from inside: `docker exec <c> getent hosts db`.

| Verbatim output | Fix |
|---|---|
| `Bind for 0.0.0.0:5432 failed: port is already allocated` | Another container: `docker ps --filter publish=5432`. Host process: `Get-NetTCPConnection -LocalPort 5432` (PS) / `lsof -i :5432` (POSIX). Change the PUBLISHED side (`"5433:5432"`) |
| `exec format error` | CPU arch mismatch (arm64 vs amd64) — build/pull with `--platform linux/amd64` or a multi-arch tag |
| `toomanyrequests: You have reached your pull rate limit` | Docker Hub anonymous cap — `docker login` or use a mirror |
| `denied: requested access to the resource is denied` (push) | Not logged in / image not tagged `registry/namespace/name` — retag then push |

## Volumes & permissions

- `docker compose down` keeps named volumes; `down -v` DELETES them — data-loss gate: list what dies first (`docker volume ls`) and say so before running it.
- Bind-mount `EACCES`/permission denied on Linux: container uid ≠ host file owner — set `user: "1000:1000"` in compose (match `id -u`) or chown in the entrypoint.
- Famous Postgres trap: editing `POSTGRES_PASSWORD` in compose does NOT change an already-initialized cluster (it only applies on first init) — auth keeps failing until you `ALTER USER` inside, or wipe the volume (data loss, gate above).

## Disk hygiene

```sh
docker system df    # images / containers / volumes / build cache — get numbers first
```

Prune ladder, safest first: `docker builder prune -f` → `docker image prune -f` (dangling only) → `docker image prune -a` (all unused tags) → volumes ONLY by name after listing. Verbatim `no space left on device` → run the ladder; on WSL2 also compact the VHDX afterwards.

## Done-gates

- **Image done** = container runs AND the app answers from the HOST on the published port (`curl -sS localhost:3000/health`) — `docker build` exit 0 is "compiled", not "works".
- **Compose stack done** = `docker compose up -d` → every service reports healthy in `compose ps`, logs clean for 60s, and the stack survives `docker compose restart`.
- **Cleanup done** = `docker system df` numbers reported before AND after.
