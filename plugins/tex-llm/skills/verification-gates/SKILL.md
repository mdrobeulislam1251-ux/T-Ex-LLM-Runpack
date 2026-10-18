---
name: verification-gates
description: Use whenever T-Ex is about to declare any task done, hand off work, or report on a build/command that exited 0 — provides the per-artifact-type run-verification recipe (exact commands, pass/fail gates, done-report format) that proves the artifact actually runs, not merely compiles.
---

# Verification Gates — Done Means Run-Verified

Exit code 0 means "compiled", never "works". A linker can succeed on a binary that crashes at
startup; a bundler can emit a page that white-screens; a migration script can parse and still
corrupt a schema. DONE-GATE, universal form: **the build exits 0 AND the artifact exists at its
expected path AND the artifact demonstrably runs** (answers a request, opens a window, produces
correct output, survives a rollback). Anything less is reported as **"compiled, not run-verified"**
— those exact words, no rounding up.

Every value below (port, binary name, health route, service name, DB URL) is probed from the
project or the environment at verification time — never assumed from memory or habit.

## Step 0 — Probe the facts you need

```sh
# POSIX — port and health route from the project's own files:
grep -rEn 'PORT|listen|--port' .env* *.json *.toml *.yaml 2>/dev/null | grep -v node_modules | head -5
grep -rEn '"/(health|healthz|ping|ready|status)"' src/ app/ 2>/dev/null | head -5
```
```powershell
# PowerShell equivalents:
Get-ChildItem .env*,*.json,*.toml,*.yaml -ErrorAction SilentlyContinue | Select-String -Pattern 'PORT|listen'
Get-ChildItem src,app -Recurse -Include *.* -ErrorAction SilentlyContinue | Select-String -Pattern '"/(health|healthz|ping|ready|status)"' | Select-Object -First 5
```
No health route found → use `/` and say so in the done report. Binary/artifact name comes from the
build output or manifest (`Cargo.toml [package] name`, `package.json "main"`, `*.csproj`), not from guessing.

## The exit-code trap (read before trusting any build result)

Piping build output through `tee`/`tail` replaces the exit code with the LAST pipe stage's — a
failed build reports 0 and silently passes the gate.

```bash
# WRONG — prints 0 even when cargo build FAILED (exit status is tail's):
cargo build 2>&1 | tee build.log | tail -40 ; echo $?

# RIGHT — pipefail makes the pipeline return cargo's status:
set -o pipefail; cargo build 2>&1 | tee build.log | tail -40 ; echo $?
# Alternatives: run the build bare and read the log after, or check ${PIPESTATUS[0]} (bash).
```

PowerShell's version of the same trap: `$LASTEXITCODE` holds the exit code of the **last native
executable** that ran — piping native→native clobbers it.

```powershell
# WRONG — $LASTEXITCODE is findstr's, not the build's. findstr exits 1 when it finds NO match,
# so a CLEAN build reports failure and a FAILED build can report 0:
npm run build 2>&1 | findstr /i "error" ; $LASTEXITCODE

# RIGHT — Tee-Object is a cmdlet, not a native exe, so $LASTEXITCODE stays the build's;
# capture it immediately, before any other native command runs:
npm run build 2>&1 | Tee-Object build.log ; $buildExit = $LASTEXITCODE ; $buildExit
```

Rule: capture the build's exit code in the same statement or the very next one. Any intervening
native command (git, curl, findstr) overwrites it.

## Per-artifact recipes

| Artifact type | Gate (ALL must hold) |
|---|---|
| CLI tool | `--help` exits 0 with usage text AND one real invocation exits 0 with expected output |
| HTTP server | process starts, health endpoint returns expected status AND body, process killed cleanly |
| Web frontend | build exits 0, artifact dir non-empty, served page returns HTTP 200 with real markup |
| Desktop app | process alive after settle time AND a window/title is present |
| Library/package | imports AND one public function returns a correct value — a green build proves neither |
| Script | run against a fixture input; output diffs clean against expected |
| DB migration | applies to a SCRATCH db, schema verified, rollback applied and verified — never live-first |
| Config change | syntax check passes, service reloads, stays active, health re-check passes |

### CLI tool
```sh
# POSIX ("$BIN" = path from the build output, e.g. ./target/debug/<name>):
"$BIN" --help ; echo "exit=$?"                      # expect exit=0 AND usage text, not a stack trace
"$BIN" <real-subcommand> <real-input> ; echo "exit=$?"   # a real invocation — --help alone proves argv parsing only
```
```powershell
& $bin --help ; "exit=$LASTEXITCODE"
& $bin <real-subcommand> <real-input> ; "exit=$LASTEXITCODE"
```
Check the OUTPUT, not just the code: a tool that exits 0 printing nothing when output was expected fails the gate.

### HTTP server
```sh
# POSIX — start, poll health (10 tries x 1 s), assert status+body, kill:
LOG=$(mktemp) ; $START_CMD >"$LOG" 2>&1 & SVPID=$!
for i in $(seq 10); do curl -fsS "http://localhost:$PORT$HEALTH" >/dev/null 2>&1 && break; sleep 1; done
CODE=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$PORT$HEALTH")
BODY=$(curl -s "http://localhost:$PORT$HEALTH")
kill "$SVPID"
echo "status=$CODE body=$BODY"      # gate: status matches expectation (usually 200) AND body is the real payload
```
```powershell
$p = Start-Process $startExe -ArgumentList $startArgs -PassThru -RedirectStandardOutput sv.log -RedirectStandardError sv.err
$r = $null ; foreach ($i in 1..10) { try { $r = Invoke-WebRequest "http://localhost:$port$health" -UseBasicParsing -TimeoutSec 2 ; break } catch { Start-Sleep 1 } }
"status=$($r.StatusCode) body=$($r.Content)"
Stop-Process -Id $p.Id
```
Server that exits before the first poll → read `$LOG`/`sv.err` BEFORE retrying; the answer is in there.

### Web frontend
```sh
# POSIX: build, confirm output, serve, hit it:
$BUILD_CMD && ls "$OUT_DIR"/index.html || { echo "no artifact"; exit 1; }
(cd "$OUT_DIR" && python3 -m http.server "$PORT" >/dev/null 2>&1 &) ; sleep 2
curl -s -o /dev/null -w '%{http_code}\n' "http://localhost:$PORT/"      # gate: 200
curl -s "http://localhost:$PORT/" | grep -ci '<div\|<main\|<app'        # gate: >= 1 — a 200 on an empty shell passes nothing
```
```powershell
& $buildCmd ; if (-not (Test-Path "$outDir\index.html")) { "no artifact" ; return }
# serve with any static server the project has (npx serve, python -m http.server), then:
(Invoke-WebRequest "http://localhost:$port/" -UseBasicParsing).StatusCode        # 200
```
HTTP 200 + non-empty markup is the floor. If the page is JS-rendered and Playwright (or another
headless browser) is already in the project, load `/` headless and assert one real selector renders;
otherwise report "served 200, rendering NOT browser-verified".

### Desktop app
```powershell
Start-Process $exePath ; Start-Sleep 5
$proc = Get-Process $procName -ErrorAction Stop | Select-Object Id, MainWindowTitle
$proc   # gate: process listed AND MainWindowTitle NON-EMPTY = a window actually opened
Stop-Process -Name $procName
```
```sh
# Linux:
"$BIN" >"$(pwd)/run.log" 2>&1 & APID=$! ; sleep 5
kill -0 "$APID" && echo ALIVE || { echo DEAD; cat run.log; }
command -v xdotool >/dev/null && xdotool search --pid "$APID" getwindowname %@ \
  || (command -v wmctrl >/dev/null && wmctrl -lp | grep "$APID")
```
Process alive but no window tooling / no display → report exactly "process alive, window NOT
visually verified" — never round that up to "launched".

### Library / package
Build success proves compilation; the gate is import + one real call:
```sh
python -c "import $PKG; print($PKG.__name__); print($PKG.$FN($SAMPLE_ARGS))"     # Python
node -e "const m=require('$ENTRY'); console.log(m.$FN($SAMPLE_ARGS))"            # Node ($ENTRY = package.json \"main\")
cargo test --doc   # Rust: doc-tests exercise the public API as a consumer would
```
Gate: the call returns a plausibly correct value — not merely "no exception".

### Script
```sh
"$SCRIPT" tests/fixtures/input.txt > actual.out ; echo "exit=$?"
diff tests/fixtures/expected.out actual.out && echo PASS      # empty diff + exit 0 = pass
```
```powershell
& $script tests\fixtures\input.txt > actual.out ; "exit=$LASTEXITCODE"
git diff --no-index tests\fixtures\expected.out actual.out    # exit 0 = identical; works on both OSes
```
No fixture exists → create one from a real (sanitized) input first. A script never run on data is not done.

### DB migration
Never apply to the live database first. Scratch DB via disposable container (trust auth = no
password exists, nothing secret-shaped to leak):
```sh
docker run -d --rm --name mig-verify -e POSTGRES_HOST_AUTH_METHOD=trust -p 5499:5432 postgres:16
sleep 5 ; SCRATCH="postgresql://postgres@localhost:5499/postgres"
$MIGRATE_UP_CMD    # the project's own tool: alembic upgrade head / npx prisma migrate deploy / flyway migrate — pointed at $SCRATCH
psql "$SCRATCH" -c "\d <changed_table>"                     # gate 1: new columns/indexes present as designed
$MIGRATE_DOWN_CMD  # alembic downgrade -1 / equivalent
psql "$SCRATCH" -c "\d <changed_table>"                     # gate 2: schema reverted cleanly
docker stop mig-verify
```
Migration tool has no down-path (e.g. prisma migrate) → say so under NOT VERIFIED; do not claim
rollback-tested. Only after both gates pass does the migration touch a real environment.

### Config change
```sh
# 1. Syntax-validate with the tool's own checker BEFORE reload (probe which applies):
nginx -t            # or: sshd -t | visudo -c | promtool check config | haproxy -c -f <file>
# 2. Reload + confirm the service survived:
sudo systemctl reload "$SVC" && systemctl is-active "$SVC"   # gate: "active"
journalctl -u "$SVC" --since "-2 min" -p err --no-pager      # gate: no new error lines
# 3. Re-run the service's health check (HTTP recipe above, or the port answers).
```
```powershell
Restart-Service $svc ; (Get-Service $svc).Status              # gate: Running
Get-EventLog -LogName Application -Newest 20 -EntryType Error -ErrorAction SilentlyContinue
```
A config change with no post-reload health re-check is NOT verified — reload success only proves the file parsed.

## Failure decoder (verbatim message → meaning → move)

| Observed | Meaning | Move |
|---|---|---|
| `curl: (7) Failed to connect to localhost port <p>: Connection refused` | nothing listening | wrong port (re-probe config) or process died at startup — read the launch log FIRST, then retry |
| `curl: (52) Empty reply from server` | listening but handler crashed mid-response | server log has the stack trace; fix before re-polling |
| `MainWindowTitle` prints empty after 5 s | process alive, no window | wait +5 s once; still empty = init hang or render crash — check app log, report not-launched |
| `Gtk-WARNING **: cannot open display:` | no GUI session on this host | report "runs headless-unverified"; do not fake a pass |
| `Error: Cannot find module '<entry>'` from `node -e` | wrong entry path | read `package.json` `"main"`/`"exports"` — verify against the real entry, not a guessed one |
| `findstr` exits 1 after a clean build | findstr found no match — NOT a build failure | you hit the PowerShell pipe trap above; re-capture `$LASTEXITCODE` correctly |

Same verification failure 3 times with no new information = stop and report (tried X, saw Y, stuck
because Z) — no fourth identical attempt.

## Done report (mandatory format)

```
VERIFIED: <artifact> — <which gate passed>
RAN:          <the exact commands executed>
OBSERVED:     <verbatim evidence: exit codes, HTTP status + body snippet, window title, diff result>
NOT VERIFIED: <what was NOT exercised — never empty>
```

NOT VERIFIED is never blank; there is always an unexercised surface ("only /health hit — auth
routes untested", "window opened — no control clicked", "up-migration verified — tool has no
down-path"). Claiming a gate passed without pasting the observed evidence is the same violation as
skipping the gate.
