# tex-agent-runner — event-driven Claude, triggered by Linear

The "loop engineering" done right: **no polling.** A Linear issue labelled `claude-fix`
fires a webhook → n8n verifies it → n8n calls this runner **once** → a headless Claude
(on your Max 20x plan) fixes it on a branch and comments the result back. The agent exists
only for the seconds it's working one issue.

```
Linear issue + label "claude-fix"
   → Linear webhook (signed)
   → n8n tex-linear-events   (verify Linear-Signature + check label)
   → POST http://172.18.0.1:8799/run   (x-tex-runner-token)
   → tex-agent-runner  (this service, user=texagent)
        clone/fetch repo · branch claude/<id> · `claude -p` (acceptEdits, scoped tools)
        commit · push branch (if GH_TOKEN) · comment back VIA the n8n gateway
   → sleep
```

## Security model (why this is safe to leave running)
- **Unprivileged user.** Runs as `texagent` — no sudo, no SSH keys → it **cannot reach the
  fleet** even though it can run bash. Blast radius = its own home dir.
- **Token-gated trigger.** Only n8n can call `/run` (shared `RUNNER_TOKEN`), and n8n only
  fires on a **signature-verified** Linear webhook carrying the `claude-fix` label.
- **Branch only, never main.** Pushes `claude/<id>`; you open/merge the PR. Nothing auto-merges.
- **Linear key stays in n8n.** The runner reports back through the gateway — it never holds it.
- **One at a time.** Serialized (`busy` flag) so concurrent issues don't collide on the clone.

## Auth — runs on your Max 20x, not API credits
Claude authenticates with a subscription OAuth token, not an API key:
```bash
sudo -u texagent claude setup-token      # opens a URL; log in with the 20x account
```
Paste the token into `CLAUDE_CODE_OAUTH_TOKEN` in `/etc/tex-agent-runner.env`, then
`systemctl restart tex-agent-runner`. Heavy automated use can still hit subscription rate
limits — if that bites, put a BYOK API key on the box instead and keep 20x for interactive work.

## Install (on aidata)
```bash
cd /opt  &&  git clone <repo> tex-src   # or scp templates/agent-runner/*
bash /path/to/templates/agent-runner/install.sh
```
The installer creates `texagent`, drops the service in `/opt/tex-agent-runner`, generates
`RUNNER_TOKEN`, copies `TEX_GATEWAY_TOKEN` from the n8n `.env`, and starts systemd.
`GET /health` → `{"ok":true,"authed":<token set?>,"busy":false}`.

## n8n wiring (the trigger)
In `tex-linear-events`, after the webhook: (1) a Code node verifies `Linear-Signature`
(HMAC-SHA256 of the raw body with the webhook signing secret); (2) an IF node passes only
events whose issue carries the `claude-fix` label; (3) an HTTP Request node POSTs to
`http://172.18.0.1:8799/run` with header `x-tex-runner-token` and body
`{identifier, title, description, issueId}`. Register the webhook URL in Linear →
Settings → API → Webhooks and copy its signing secret into n8n.

## Firewall note (done on aidata)
`/run` binds `0.0.0.0:8799` (8787 was already taken by the ES→Supabase transfer-api).
ufw is active with a default-DROP INPUT policy, so the n8n container is allowed through a
single scoped rule — the same pattern the transfer-api uses:
`ufw allow from 172.18.0.0/16 to any port 8799 proto tcp`. Tailnet/public cannot reach it;
the `RUNNER_TOKEN` is the backstop. Verified: the n8n container reaches `172.18.0.1:8799`.

## v1 limits (honest)
- **Branch push needs `GH_TOKEN`** (fine-grained, contents:write). Without it, the runner
  still fixes + commits locally and comments the summary — you just won't get a remote branch.
- **PR is opened by you** (or add a `gh pr create` step once a token is present). No auto-merge by design.
- One repo per run (from `REPO_URL` or the job's `repo`).
