---
name: systematic-debugging
description: Use whenever anything is broken, flaky, or unexplained — failing test, crash, wrong output, works-here-not-there, intermittent error — BEFORE proposing or applying any fix; it enforces reproduce-first, one-hypothesis-at-a-time, and a hard stop after 3 failed fix attempts.
---

# Systematic Debugging — T-Ex Method

Debugging is state reading, not guessing. Every step below either observes real state or discriminates between hypotheses. Nothing here assumes an OS, path, or stack — probe everything on the machine you are actually on.

## 1. The Iron Rule — Reproduce Before You Fix

No fix attempt until a reproduction exists. A reproduction is BOTH of:

1. **A deterministic command** — one line anyone could paste into a shell on this machine that triggers the failure. "Click around until it breaks" is not a reproduction; script the click (curl the endpoint, run the one test, pipe the input file) until it is.
2. **The observed failure output, captured verbatim** — redirect it to a file, don't trust scrollback:

```sh
# POSIX
<failing-command> >repro.out 2>&1; echo "exit=$?" >>repro.out
```

```powershell
# PowerShell
<failing-command> *> repro.out; "exit=$LASTEXITCODE" >> repro.out
```

REPRO-GATE (pass/fail): the command fails the same way **2 consecutive runs** (for flaky bugs: record N failures out of M runs, e.g. "3/20" — that ratio is now part of the repro). FAIL = you do not yet have a bug you can fix; you have a rumor. The same command re-run green is later the only acceptable proof of fix.

If you cannot reproduce after 15 minutes of honest attempts, say so plainly and switch to instrumenting (add logging at the suspected seam, wait for the next natural occurrence) — do not "fix" an unreproduced bug and declare victory.

## 2. Read the Actual State — Toolkit

Run the relevant probes before forming any hypothesis. Both platform variants given; pick by the shell you are in.

**Processes (what is actually running):**

```sh
ps aux | sort -rk3 | head -15        # POSIX; top CPU. macOS-safe (no GNU --sort)
```
```powershell
Get-Process | Sort-Object CPU -Descending | Select-Object -First 15 Id,ProcessName,CPU,WS
```

**Listening ports (who owns the port you think is yours):**

```sh
ss -tlnp                              # Linux
lsof -iTCP -sTCP:LISTEN -n -P         # macOS (ss absent)
```
```powershell
Get-NetTCPConnection -State Listen | Sort-Object LocalPort |
  Select-Object LocalAddress,LocalPort,@{n='Proc';e={(Get-Process -Id $_.OwningProcess).ProcessName}}
```

**Recent logs (last 10 minutes beats last 10 days):**

```sh
journalctl -u <service> --since "10 min ago" --no-pager   # Linux systemd service
docker logs --tail 100 --timestamps <container>           # container, any host
tail -100 <logfile>                                       # plain file logs
```
```powershell
Get-WinEvent -LogName Application -MaxEvents 40 |
  Where-Object { $_.LevelDisplayName -in 'Error','Warning' } |
  Select-Object TimeCreated,ProviderName,Message
docker logs --tail 100 --timestamps <container>           # same command on Windows
```

**Environment of a RUNNING process (not your shell's env — the process's):**

```sh
tr '\0' '\n' < /proc/<PID>/environ    # Linux
ps eww <PID>                          # macOS: env appended to the command line
```
```powershell
(Get-CimInstance Win32_Process -Filter "ProcessId=<PID>").CommandLine   # full launch cmdline + args
# Full env block of a foreign process needs Process Explorer / SysInternals; say so rather than guess.
```

**What changed recently (files touched in the last hour — bugs correlate with change):**

```sh
find . -mmin -60 -type f -not -path '*/.git/*' -not -path '*/node_modules/*' | head -20
```
```powershell
Get-ChildItem -Recurse -File |
  Where-Object { $_.FullName -notmatch '\\(\.git|node_modules)\\' -and $_.LastWriteTime -gt (Get-Date).AddMinutes(-60) } |
  Sort-Object LastWriteTime -Descending | Select-Object -First 20 FullName,LastWriteTime
```

**Which binary is actually on PATH (version-mismatch discovery):**

```sh
which -a node && node --version       # -a lists ALL matches in PATH order — mismatch tell
type -a python3                       # also reveals aliases/functions shadowing the binary
```
```powershell
Get-Command node -All | Select-Object Name,Version,Source   # -All = every PATH hit, first wins
node --version
```

Cross-check the resolved version against what the project declares (`.nvmrc`, `package.json` engines, `pyproject.toml` requires-python, `go.mod`, `rust-toolchain.toml`). Shell-resolved binary ≠ what a service/cron/CI runs — check the unit file / task definition for its own PATH.

## 3. Hypothesis Discipline

- **One hypothesis at a time.** Changing two things and seeing green teaches you nothing — you cannot tell which change mattered, and one of them may be a new latent bug.
- **Cheapest discriminating test first.** Rank candidate tests by (seconds to run) vs (hypotheses eliminated). A 2-second `which -a` that splits "wrong binary" from "wrong code" beats a 10-minute rebuild every time.
- **Keep a ledger.** For each test, write one line: `TESTED: <command> → <result> → RULES OUT: <hypothesis>`. When someone (including future you) asks "did you check X", the ledger answers. A hypothesis ruled out stays ruled out — do not circle back to it without new evidence.
- A test that confirms nothing and rules out nothing was the wrong test. Pick tests whose two possible outcomes point to different causes.

## 4. Bisection Recipes

Bisection converts "somewhere in N things" into log2(N) tests. Three flavors:

**Git bisection (which commit broke it)** — automate it, never bisect by hand:

```sh
git bisect start
git bisect bad HEAD
git bisect good <last-known-good-tag-or-sha>
git bisect run ./bisect-test.sh
git bisect reset            # ALWAYS reset when done — a forgotten bisect strands HEAD
```

`bisect-test.sh` (exit 0 = good, 1–124 = bad, **125 = skip this commit**):

```sh
#!/bin/sh
npm ci --silent || exit 125          # can't build here ≠ has the bug — skip, don't blame
npm test -- --run failing.test.ts    # scoped to the ONE failing test, not the whole suite
```

400 commits = 9 automated builds, minutes not hours. Windows note: `git bisect run` executes the script via git's own sh — write it POSIX even on Windows.

**Config bisection (which setting broke it):** copy the config, comment out half, re-run the repro. Failure persists → cause is in the live half; failure gone → in the commented half. Recurse. 64 lines of config = 6 runs to the guilty line. Works identically on env files, feature flags, middleware stacks, and browser extension lists.

**Data bisection (minimal failing input):** a 10,000-row file fails → `split -l 5000 data.csv part_` (POSIX) or `Get-Content data.csv | Select-Object -First 5000 | Set-Content half.csv` (PowerShell), feed each half, recurse to the single failing row/record. The minimal input usually *names the bug* (the row with the NUL byte, the 5MB field, the date `2026-02-29`). Stop shrinking when removing anything else makes the failure disappear.

## 5. Trap Bugs and Their Tells

| Trap | Tell (what you actually observe) | Confirm + fix |
|---|---|---|
| Stale build artifact | You edited the source, the error message still quotes the OLD line/text; or a `console.log`/`print` you just added never appears | Clean build: `rm -rf dist build .next target __pycache__` / `dotnet clean` / `cargo clean`, rebuild, re-run repro |
| Wrong environment | Works in shell A, fails in shell B / in the service / in CI; classic pair: `command not found` (POSIX) vs `'x' is not recognized as the name of a cmdlet` (PowerShell) | Diff the envs: `env | sort > a.env` in each, `diff a.env b.env`; PowerShell: `Get-ChildItem env: | Sort-Object Name`. Then §2 PATH probe in the failing context |
| Cache poisoning | Fails until a cache is cleared, then works — then slowly breaks again | Identify WHICH cache proved guilty (`npm cache clean --force`, `pip cache purge`, Docker layer `--no-cache`, CDN, browser). Clearing all caches "to be safe" destroys the evidence |
| Race condition | Fails ~1 in N runs; passes under a debugger or with logging added (timing changed); fails more under load | Make it worse to make it visible: run 100×, add `sleep` at the suspected interleave point. Fix the ordering (await/join/lock), never the symptom (`retry: 3` is concealment, not a fix) |
| Off-by-timezone | Fails only for certain dates, near midnight, or for users/servers in certain regions; date stored right but displays a day off | Check `TZ` env, server tz (`timedatectl` / `Get-TimeZone`), and whether the code mixes local and UTC. Repro must pin the tz: `TZ=Asia/Tokyo <cmd>` / `$env:TZ='Asia/Tokyo'; <cmd>` |
| Port squatting | `Error: listen EADDRINUSE: address already in use :::3000` or bind fails only sometimes (orphan from last run) | §2 port probe → find the owning PID → kill it or pick a free port; check for a supervisor auto-respawning it |
| Wrong cwd / relative path | `ENOENT: no such file or directory, open './config.json'` yet the file visibly exists | The process's cwd ≠ your shell's cwd. Log `pwd`/`process.cwd()` inside the process; resolve paths from the executable/module location, not cwd |
| Disk full | `ENOSPC: no space left on device`, SQLite `database or disk is full`, or writes silently truncated / zero-byte files | `df -h .` (Linux/macOS; also `df -i` — inode exhaustion reports ENOSPC with free GB) / `Get-PSDrive -PSProvider FileSystem` |
| CRLF poisoning | `/bin/sh^M: bad interpreter: No such file or directory`, or a script/YAML edited on Windows failing only on Linux | `file script.sh` → "with CRLF line terminators" confirms; fix with `dos2unix` and pin `*.sh text eol=lf` in `.gitattributes` |

If the observed behavior is "my change has no effect at all", suspect stale artifact or wrong environment FIRST — they explain ~most no-effect mysteries and each is a 30-second check.

## 6. The Stop Rule

Hard gate, no exceptions: **after 3 failed fix attempts on the same symptom, stop patching.** Attempt 4 with the same diagnosis is how bugs get buried under scar tissue. Instead:

1. **Re-read the error verbatim** — the full text from `repro.out`, top of the stack trace to the bottom, aloud-slow. Most 3-strike streaks trace to a skimmed error: the message said `permission denied` and you were fixing the path; it said module `foo-bar` and you were rebuilding `foo_bar`.
2. **Question the diagnosis, not the patch.** Write two columns: KNOW (backed by a §2 probe or the ledger) vs ASSUMED (everything else). Every assumption is now a hypothesis to test — starting with the one all three failed fixes silently shared.
3. **Report state plainly** before continuing: "Tried A, B, C; all failed with <verbatim output>; I now know X and Y; I had assumed Z, testing that next." If the KNOW column is thin, go back to §2 and read more state.

Corollary gates: same *verbatim* error 5 times total = stop and escalate to the user with the ledger — do not guess a sixth time. And a fix is only proven by the §1 repro command going green, run twice; "it should work now" is not a verification.
