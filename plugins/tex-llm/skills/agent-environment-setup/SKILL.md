---
name: agent-environment-setup
description: Use at the start on a new machine, or when the user says "make it smoother / set up my environment / same as my other computer" — provisions the agent context: Context7 and other MCP servers, git identity + branch naming, SSH fleet aliases, and a portable manifest so the SAME setup replicates across computers. Probes what exists before installing; never duplicates.
---

# Agent Environment Setup

Makes a fresh machine feel like your configured one. The doctrine: **probe what's already here, install only the gaps, and write a manifest so the next machine is one command.** Never install blind — a second copy of a tool the machine already has is the failure this skill prevents.

## Step 0 — Probe the baseline

```sh
node --version; npm --version                 # MCP servers commonly run via npx
git --version; git config --global user.name; git config --global user.email
claude mcp list 2>/dev/null                    # MCPs already configured (don't re-add these)
cat ~/.ssh/config 2>/dev/null | grep -ic '^host '   # fleet aliases present?
```
```powershell
node --version; npm --version
git --version; git config --global user.name; git config --global user.email
claude mcp list
```

Record what's PRESENT vs MISSING. Everything below acts only on the MISSING set.

## Step 1 — MCP servers (the context layer)

MCPs give the agent live capabilities. `claude mcp add` scopes matter: `--scope user` = all your projects on this machine (right for general tools like Context7); `--scope project` writes `.mcp.json` into the repo (right for project-specific servers, shared via git); `--scope local` = this project only, not shared.

**Context7 — up-to-date library docs (the "stop coding against stale APIs" server):**

```sh
# remote (simplest; may require a free Context7 API key for higher limits)
claude mcp add --transport http --scope user context7 https://mcp.context7.com/mcp
# local alternative (runs via npx, no hosted dependency):
claude mcp add --scope user context7 -- npx -y @upstash/context7-mcp
```

Verify it actually connected before claiming it's set up:

```sh
claude mcp list | grep context7        # expect: context7 ... ✓ connected (not "failed")
```

Other high-value MCPs — add per what the work needs (probe each isn't already present):

| MCP | Adds | Add (verify after) |
|---|---|---|
| Context7 | current library/framework docs | above |
| Playwright | browser automation, visual verification of frontends | `claude mcp add --scope user playwright -- npx -y @playwright/mcp@latest` |
| Filesystem | scoped file access outside cwd | `claude mcp add --scope user filesystem -- npx -y @modelcontextprotocol/server-filesystem <dir>` |
| Postgres (read) | query a DB as a tool | project-scoped; connection string via env, never inline |
| Linear | issues as tools | `claude mcp add --transport http --scope user linear https://mcp.linear.app/mcp` (see `linear-integration`) |

Rules: **secrets for MCPs go in env vars**, never in the `claude mcp add` command line (it lands in shell history). Any MCP showing `failed` in `claude mcp list` is triaged now, not left — a dead MCP silently removes a capability you'll assume you have.

## Step 2 — Git identity & branch convention

```sh
git config --global user.name  "<name>"       # only if Step 0 showed it empty
git config --global user.email "<email>"
git config --global init.defaultBranch main
git config --global pull.rebase true          # linear history
```

- **Per-project override** when a repo needs a different identity (e.g. a work email): `git config user.email "<work>"` inside that repo — overrides global for that repo only. Verify with `git config user.email` from inside it.
- **Branch naming** ties to the tracker: `<issue-id>-<slug>` (e.g. `eng-142-fix-login-loop`) so Linear/GitHub autolink the branch to the issue (`linear-integration`). One issue = one branch.
- Credential persistence so pushes don't re-prompt: `git config --global credential.helper manager` (Windows) / `store` or `osxkeychain` (mac). A PAT entered once then lands in the OS credential store.

## Step 3 — SSH fleet aliases

If this machine operates the server fleet (`server-fleet-management`) and Step 0 showed no aliases, recreate `~/.ssh/config` entries so `ssh <alias>` works:

```
Host <alias>
    HostName <tailnet-ip-or-host>
    User <account-that-exists-on-box>
```

For Tailscale fleets: the machine must first join the tailnet (`tailscale up`) and identity-based SSH needs no key here. Confirm with `ssh -o ConnectTimeout=8 <alias> hostnamectl` (the fleet skill's connect gotchas apply). Never copy private keys into a doc or the repo — they stay in `~/.ssh/` with mode 600.

## Step 3.5 — Status line, editor mode, model (the visible setup)

Replicate the terminal look and per-session prefs the user runs elsewhere.

**Status line** (`◆ <model> · <workspace> · ⎇ <branch>* · <N> changed · $<cost>`): copy `templates/statusline.sh` to `~/.claude/statusline.sh`, then add to `~/.claude/settings.json` (merge, don't replace):

```json
{
  "statusLine": { "type": "command", "command": "bash \"$HOME/.claude/statusline.sh\"" },
  "editorMode": "vim"
}
```

Windows + Git Bash: set `env.CLAUDE_CODE_GIT_BASH_PATH` to the bash exe and use an absolute POSIX path in the command (`bash "/c/Users/<you>/.claude/statusline.sh"`). Test before trusting it — pipe a sample payload:

```sh
echo '{"model":{"display_name":"Opus 4.8 (1M context)"},"workspace":{"current_dir":"'"$PWD"'"},"cost":{"total_cost_usd":3.57}}' | bash ~/.claude/statusline.sh
```

**Editor mode**: `"editorMode": "vim"` gives the built-in `-- INSERT --` / `-- NORMAL --` indicator. **Model + 1M context**: run `/model` and pick the model (e.g. `Opus 4.8 (1M context)`) — this selects the model AND its context window in one step and persists as the default; don't hand-set a model ID when a 1M variant is wanted. **Bypass permissions** (`⏵⏵`): `"permissions": { "defaultMode": "bypassPermissions" }` — auto-approves tool calls; only for a machine the user trusts, and only after they've accepted the bypass dialog once. Flag this one explicitly — it's the single security-relevant preference.

## Step 4 — Write the portable manifest (this is what makes "same as my other computer" one command)

Capture the desired setup as data so any new machine reproduces it. Store it OUTSIDE any repo that could be public (a private dotfiles repo or synced vault), values referenced by env-var name:

```json
// env-manifest.json — names/config only, NO secret values
{
  "mcp": [
    { "name": "context7",  "scope": "user", "transport": "http", "url": "https://mcp.context7.com/mcp" },
    { "name": "playwright","scope": "user", "cmd": "npx -y @playwright/mcp@latest" },
    { "name": "linear",    "scope": "user", "transport": "http", "url": "https://mcp.linear.app/mcp" }
  ],
  "git": { "user.name": "<name>", "init.defaultBranch": "main", "pull.rebase": true },
  "claude_code": { "editorMode": "vim", "statusLine": "templates/statusline.sh", "model": "Opus 4.8 (1M context) — pick via /model", "permissions.defaultMode": "bypassPermissions" },
  "ssh_aliases_source": "<private path to ssh config, e.g. a synced vault>",
  "env_vars_required": ["CONTEXT7_API_KEY", "LINEAR_API_KEY", "ANTHROPIC_API_KEY"]
}
```

Re-applying on a new machine = read the manifest, run Step 0 (probe), then add only the MCP/git/ssh entries the probe reports missing, and finally the ONE batched ask for the `env_vars_required` values (per `project-bootstrap` — never drip). The manifest is committed; the secret values never are.

## Anti-patterns

- Re-adding an MCP/git-config/alias that Step 0 already found present.
- Putting a secret (API key, token) on an `claude mcp add` / `git config` command line — it enters shell history; use env vars.
- Claiming "Context7 is set up" without `claude mcp list` showing it connected.
- Copying the manifest with real secret values filled in — names only, values in env/secret store.
- A new-machine setup that silently skips a `failed` MCP — a missing capability you'll later assume exists.

## Done-gates

- **Environment setup done** = `claude mcp list` shows every intended MCP `connected` (zero `failed`), git identity resolves, fleet aliases (if applicable) each answer `hostnamectl`, and the manifest is written.
- **Replication done** = on the second machine, running the manifest reproduces the same `claude mcp list` connected set and git identity — proven by running the probe there, not assumed.
