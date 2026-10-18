---
name: environment-recon
description: Use at the start of any session on any machine, whenever a command fails with "is not recognized" / "command not found", or before stating any fact about the OS, shell, cwd, project stack, or package manager — it probes the real environment in under 30 seconds instead of assuming.
---

# environment-recon — Probe First, On Any Machine

T-Ex runs on unknown machines by design. This skill is how a session learns where it is. Every environment fact below is obtained by running a command or reading a project file — never from memory, never from a previous session.

## Light Recon Ritual (≤30 seconds, ≤5 commands, every session)

Run before the first environment-dependent action. Skip only for pure Q&A with zero file/command contact.

**Step 1 — identify the shell.** Run this exact probe and match the output:

```
$PSVersionTable.PSVersion.ToString()
```

| Shell | Output of the probe above |
|---|---|
| PowerShell 5.1 | `5.1.26100.4202` (major 5, build tracks the OS) |
| PowerShell 7+ | `7.4.6` (major 7) |
| cmd.exe | `'$PSVersionTable.PSVersion.ToString()' is not recognized as an internal or external command, operable program or batch file.` |
| bash / zsh | syntax error or `command not found` — it is a POSIX shell, go to Step 1b |

**Step 1b — POSIX branch.** If Step 1 errored like a POSIX shell:

```sh
uname -s; echo "$0"; echo "$BASH_VERSION$ZSH_VERSION"
```

| Environment | `uname -s` | `$0` |
|---|---|---|
| Linux | `Linux` | `bash` / `-bash` / `zsh` |
| macOS | `Darwin` | usually `-zsh` (default since Catalina) |
| Git Bash on Windows | `MINGW64_NT-10.0-<build>` | `bash` — Windows paths appear as `/c/...` style |
| WSL | `Linux` | `bash` — check `uname -r` for `microsoft` to confirm WSL |

PowerShell 5.1 tell: `cmd1 && cmd2` fails with `The token '&&' is not a valid statement separator in this version.` PowerShell 7 accepts `&&`. Never chain with `&&` until the shell major version is known.

**Step 2 — confirm cwd.** `pwd` works in PowerShell (alias for `Get-Location`) and all POSIX shells; `cd` alone in cmd. Never assume the working directory survived from a prior command in agent contexts — many harnesses reset it per call. Use absolute paths obtained from `pwd`, not remembered ones.

**Step 3 — detect the stack from marker files.**

```powershell
Get-ChildItem -Force -Name | Select-Object -First 40        # PowerShell
```
```sh
ls -a | head -40                                             # POSIX
```

Match against the Marker Table below. Multiple markers = polyglot repo; name all stacks, then let the task select one.

**Step 4 — report one line, then proceed.** Format:
`Recon: <OS> / <shell+version> / cwd=<dir name> / <stack> via <package manager> (<lockfile>)`

**Light-recon gate — PASS requires all four:** shell identified by probe output (not guessed), cwd printed, stack named from a marker file actually listed, package manager named from a lockfile actually listed. Any assumed item = FAIL, redo the missing probe.

## Marker Table — Stack and Canonical Commands

| Marker file | Stack | Build | Test | Run |
|---|---|---|---|---|
| `package.json` | Node/JS/TS | `<pm> install` then `<pm> run build` | `<pm> test` | read `"scripts"` first — scripts beat guesses |
| `pyproject.toml` | Python | per lockfile (see below) | `pytest` (via the pm's runner) | read `[project.scripts]` |
| `go.mod` | Go | `go build ./...` | `go test ./...` | `go run .` |
| `Cargo.toml` | Rust | `cargo build` | `cargo test` | `cargo run` |
| `*.sln` / `*.csproj` | .NET | `dotnet build` | `dotnet test` | `dotnet run --project <dir>` |
| `pom.xml` | Java (Maven) | `mvn -q package` | `mvn test` | `java -jar target/<name>.jar` |
| `build.gradle(.kts)` | JVM (Gradle) | `./gradlew build` | `./gradlew test` | `./gradlew run` |
| `Gemfile` | Ruby | `bundle install` | `bundle exec rspec` | `bundle exec <cmd>` |
| `composer.json` | PHP | `composer install` | `./vendor/bin/phpunit` | `php -S` dev server; `artisan serve` if Laravel |
| `mix.exs` | Elixir | `mix deps.get && mix compile` | `mix test` | `mix run` / `mix phx.server` if Phoenix |

Decision rules:
- A committed wrapper beats a global tool: `gradlew` in the repo → use it (`gradlew.bat` from cmd/PowerShell, `./gradlew` from POSIX), never global `gradle`. Same for `mvnw`.
- `package.json` `"scripts"` block is the project's declared interface — read it before running any canonical command; if `"build"` exists, that is the build command, whatever it does internally.
- `Makefile` / `justfile` / `Taskfile.yml` present → open it; the project already chose its commands.

## Package Manager — The Lockfile Decides, Not Your Preference

Detect by lockfile presence, in this order. Using the wrong manager rewrites the lockfile and pollutes the diff — that alone can fail a task.

| Lockfile | Manager | Clean install (CI-safe) |
|---|---|---|
| `pnpm-lock.yaml` | pnpm | `pnpm install --frozen-lockfile` |
| `yarn.lock` | yarn | `yarn install --immutable` (v2+) / `--frozen-lockfile` (v1) |
| `bun.lockb` / `bun.lock` | bun | `bun install` |
| `package-lock.json` | npm | `npm ci` |
| `uv.lock` | uv | `uv sync` — run things via `uv run <cmd>` |
| `poetry.lock` | poetry | `poetry install` — run via `poetry run <cmd>` |
| `Pipfile.lock` | pipenv | `pipenv sync` |
| `requirements.txt` only | pip + venv | `python -m venv .venv` then activate and `pip install -r requirements.txt` |

Conflict rules (multiple lockfiles present):
1. `"packageManager"` field in `package.json` (e.g. `"pnpm@9.1.0"`) is authoritative — obey it.
2. Otherwise the most recently modified lockfile wins.
3. Either way, report the conflict in one line; do not silently delete a lockfile.

POSIX venv activate: `. .venv/bin/activate` — PowerShell: `.venv\Scripts\Activate.ps1` — cmd: `.venv\Scripts\activate.bat`.

## Toolchain Probes and What Missing Looks Like

Version probes with expected output shapes:

```sh
node --version     # v22.11.0        — strip the leading "v" before comparing
python --version   # Python 3.12.4   — on Linux/macOS, if missing try: python3 --version
git --version      # git version 2.45.1.windows.1  (suffix names the platform build)
docker info        # must contain a "Server:" section — client-only output means daemon down
```

Missing-command errors, verbatim per shell — recognizing which one you got also confirms the shell:

| Shell | Verbatim error for missing `node` |
|---|---|
| PowerShell | `The term 'node' is not recognized as the name of a cmdlet, function, script file, or operable program.` |
| cmd.exe | `'node' is not recognized as an internal or external command, operable program or batch file.` |
| bash | `bash: node: command not found` |
| zsh | `zsh: command not found: node` |

Fix path, in order:
1. **Installed but not on this session's PATH?** Probe: `where.exe node` (Windows) / `command -v node` (POSIX). Freshly installed tools are invisible to already-open shells. PowerShell refresh without reopening: `$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')`. POSIX: `hash -r` after PATH edits, or open a new login shell.
2. **Genuinely missing?** Name the install command for the detected OS — `winget install <id>` (Windows), `brew install <pkg>` (macOS), `apt-get install <pkg>` / `dnf install <pkg>` (Linux) — run small CLI installs, list-and-wait for approval on multi-GB installs (SDKs, IDEs, Docker Desktop).

Known traps mapped to fixes:

- Windows, `python --version` prints `Python was not found; run without arguments to install from the Microsoft Store, or disable this shortcut from Settings > Manage App Execution Aliases.` — that is the Store stub, not Python. Fix: probe `py --version` (the Python launcher, expect `Python 3.12.4`); if `py` also missing, install Python, then prefer `py` on Windows.
- Linux, `python: command not found` but `python3 --version` works — many distros ship only `python3`. Use `python3` and `python3 -m pip`; do not alias globally on someone else's machine.
- `docker info` on Windows ends with `error during connect: ... The system cannot find the file specified.` — Docker Desktop daemon not running. Fix: start Docker Desktop, re-probe until the `Server:` section appears.
- `docker info` on Linux: `Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?` — daemon down (`systemctl start docker`) or user lacks group membership (`docker` group; takes a re-login).
- `git --version` fine but `git push` prompts or hangs — credential/agent state, not a toolchain problem; report it, do not reinstall git.

## Deep Recon — Servers and Ops Boxes

Run only when the task touches services, deploys, resources, or "why is X slow/down". Not part of light recon.

| Inventory | Windows (PowerShell) | Linux |
|---|---|---|
| Running services | `Get-Service \| Where-Object Status -eq 'Running'` | `systemctl list-units --type=service --state=running` |
| Listening ports | `Get-NetTCPConnection -State Listen \| Sort-Object LocalPort \| Select-Object LocalAddress,LocalPort,OwningProcess` then `Get-Process -Id <pid>` to name the owner | `ss -tlnp` (fallback: `netstat -tlnp`) |
| Disk | `Get-Volume \| Select-Object DriveLetter,FileSystemLabel,SizeRemaining,Size` | `df -h` |
| Memory | `Get-CimInstance Win32_OperatingSystem \| Select-Object @{n='FreeGB';e={[math]::Round($_.FreePhysicalMemory/1MB,1)}},@{n='TotalGB';e={[math]::Round($_.TotalVisibleMemorySize/1MB,1)}}` | `free -h` |
| Load / top consumers | `Get-Process \| Sort-Object CPU -Descending \| Select-Object -First 10 Name,Id,CPU,WorkingSet` | `uptime` then `top -bn1 \| head -15` |
| Other humans logged in | `quser` | `w` |

Thresholds that change your behavior:
- Free disk < 10% of volume OR < 5 GB absolute → flag it and get an explicit go-ahead before any build, install, or log-heavy operation.
- Free RAM < 500 MB → do not start heavy builds or containers; report first.
- The port your task needs already shows LISTEN → identify the owning process by PID before binding, killing, or picking a new port. Never kill a listener you have not named.
- Other users in `quser` / `w` output → this is a shared box; no reboots, no service restarts without approval (defer to `server-ops-safety`).

**Deep-recon gate — PASS:** services, ports, disk, memory each captured by an actual command in this session, with the four threshold checks evaluated. Quoting numbers you did not just probe = FAIL.

## Doctrine: Probed Facts Expire

1. **Never write a probed fact into a file as if permanent.** No baking "Node v22 is installed" into a README, script, config, or skill. Machines update, sessions move hosts, PATH changes between shells.
2. **Re-probe per session.** A fact's lifetime is the session that probed it. New session = fresh light recon, even on a machine that looks familiar.
3. **If a memory file must record environment state** (a project's own convention), every entry carries a `verified_on` date and is treated on read as a stale hint to re-verify, never as truth.
4. **Scripts you write must probe, not assume.** A script that needs the OS branches on its own probe (`$IsWindows` / `uname`) at runtime; it never hardcodes the answer you found today.
5. **Hardcoding an absolute path, hostname, username, or port you probed into produced output is a portability violation** — use relative paths, env vars, or a runtime probe (Prime Directive 6).

The test: if this repo were cloned onto a random machine tomorrow, does everything you wrote today still work? If any file you touched answers "no because it remembers this machine", fix it before reporting done.
