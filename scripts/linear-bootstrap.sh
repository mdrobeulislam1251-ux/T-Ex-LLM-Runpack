#!/usr/bin/env bash
# linear-bootstrap.sh — create the "T-Ex LLM" project in Linear + labels + seeded
# starting backlog (every issue ends with runnable acceptance checks).
#
# RULE (user's): the Linear API key lives ONLY inside n8n as a credential.
# This script never touches the key — every call routes through the n8n gateway
# webhook (templates/n8n/claude-gateway.workflow.json), which attaches the key
# server-side. Claude/dev machines hold only webhook access (base URL + token).
#
# Usage:   N8N_BASE=https://<your-n8n> TEX_GATEWAY_TOKEN=... [TEAM_KEY=TEX] \
#            bash scripts/linear-bootstrap.sh
#          (or put N8N_BASE + TEX_GATEWAY_TOKEN in .env and `set -a; . ./.env`)
# N8N_BASE examples: tailnet http://100.89.97.60:5678  ·  public https://n8n.<domain>
# Prereq:  tl-n8n online, gateway workflow imported+active, Linear key stored as
#          the n8n credential, TEX_GATEWAY_TOKEN set in n8n's environment.
# Status:  authored 2026-07-22; NOT yet run-verified (needs the live gateway) —
#          first run is the verification, per pipeline done-gates.
set -euo pipefail

: "${N8N_BASE:?Set N8N_BASE (your n8n base URL, no trailing slash)}"
: "${TEX_GATEWAY_TOKEN:?Set TEX_GATEWAY_TOKEN (the gateway webhook token)}"
GATEWAY="$N8N_BASE/webhook/tex-claude-gateway"
command -v jq >/dev/null || { echo "jq is required"; exit 1; }

gql() { # $1 = full JSON payload {query, variables} — proxied by n8n, key stays server-side
  curl -sS -X POST "$GATEWAY" \
    -H "Content-Type: application/json" \
    -H "x-tex-token: $TEX_GATEWAY_TOKEN" \
    -d "$1"
}

# ── 0. Verify gateway + key + pick the team ──────────────────────────────────
ME=$(gql '{"query":"{ viewer { id name email } teams { nodes { id name key } } }"}')
echo "$ME" | jq -e '.data.viewer.id' >/dev/null || { echo "Gateway/key check failed: $ME"; exit 1; }
echo "Gateway OK. Authed (via n8n credential) as: $(echo "$ME" | jq -r '.data.viewer.name')"

if [ -n "${TEAM_KEY:-}" ]; then
  TEAM_ID=$(echo "$ME" | jq -r --arg k "$TEAM_KEY" '.data.teams.nodes[] | select(.key==$k) | .id')
else
  TEAM_ID=$(echo "$ME" | jq -r '.data.teams.nodes[0].id')
fi
[ -n "$TEAM_ID" ] && [ "$TEAM_ID" != "null" ] || { echo "No team found (set TEAM_KEY=...). Teams: $(echo "$ME" | jq -c '.data.teams.nodes')"; exit 1; }
echo "Team: $(echo "$ME" | jq -r --arg id "$TEAM_ID" '.data.teams.nodes[] | select(.id==$id) | "\(.name) (\(.key))"')"

# ── 1. Project (skip if exists) ──────────────────────────────────────────────
EXISTING=$(gql '{"query":"{ projects(filter:{name:{eq:\"T-Ex LLM\"}}) { nodes { id url } } }"}')
PROJECT_ID=$(echo "$EXISTING" | jq -r '.data.projects.nodes[0].id // empty')
if [ -n "$PROJECT_ID" ]; then
  echo "Project already exists: $(echo "$EXISTING" | jq -r '.data.projects.nodes[0].url')"
else
  PAYLOAD=$(jq -n --arg tid "$TEAM_ID" '{query:"mutation($input:ProjectCreateInput!){projectCreate(input:$input){success project{id url}}}",variables:{input:{name:"T-Ex LLM",teamIds:[$tid],description:"The Full Company Runpack — building T-Ex LLM itself. Pipeline: runpacks/web-dev-pipeline.md (Cursor drafts, Grok reviews, Claude executes, n8n automates)."}}}')
  RES=$(gql "$PAYLOAD")
  PROJECT_ID=$(echo "$RES" | jq -r '.data.projectCreate.project.id // empty')
  [ -n "$PROJECT_ID" ] || { echo "projectCreate failed: $RES"; exit 1; }
  echo "Project created: $(echo "$RES" | jq -r '.data.projectCreate.project.url')"
fi

# ── 2. Labels ────────────────────────────────────────────────────────────────
declare -A LABELS=( [bug]="#e5484d" [feature]="#26b5ce" [deploy]="#f2994a" [research]="#9b8afb" [spec]="#4cb782" [blocked-gate]="#eb5757" )
for name in "${!LABELS[@]}"; do
  PAYLOAD=$(jq -n --arg tid "$TEAM_ID" --arg n "$name" --arg c "${LABELS[$name]}" '{query:"mutation($input:IssueLabelCreateInput!){issueLabelCreate(input:$input){success}}",variables:{input:{teamId:$tid,name:$n,color:$c}}}')
  R=$(gql "$PAYLOAD")
  echo "$R" | jq -e '.data.issueLabelCreate.success' >/dev/null 2>&1 \
    && echo "label + $name" || echo "label ~ $name (exists or failed: $(echo "$R" | jq -c '.errors[0].message // empty'))"
done

# ── 3. Seed the starting backlog ─────────────────────────────────────────────
seed() { # $1 title, $2 description
  PAYLOAD=$(jq -n --arg tid "$TEAM_ID" --arg pid "$PROJECT_ID" --arg t "$1" --arg d "$2" \
    '{query:"mutation($input:IssueCreateInput!){issueCreate(input:$input){success issue{identifier url}}}",variables:{input:{teamId:$tid,projectId:$pid,title:$t,description:$d}}}')
  R=$(gql "$PAYLOAD")
  ID=$(echo "$R" | jq -r '.data.issueCreate.issue.identifier // empty')
  [ -n "$ID" ] && echo "issue + $ID  $1" || echo "issue ! FAILED  $1 -> $(echo "$R" | jq -c '.errors // .')"
}

seed "Port + scrub the 10 Outbound cold-email skills into the runpack" \
"Move skills from the Outbound agent folder into plugins/tex-llm/skills/, credentials stripped to env-var names.

## Acceptance checks
- [ ] All 10 skills listed by the marketplace after /plugin refresh
- [ ] \`git grep -iE 'password|secret|api[_-]?key' plugins/tex-llm/skills/\` shows env-var NAMES only
- [ ] Each SKILL.md has valid frontmatter (name + description)"

seed "Build /forge-skill command (author -> verify -> fix loop)" \
"Command that authors a new skill, validates frontmatter/structure, and fixes its own findings.

## Acceptance checks
- [ ] /forge-skill produces a skill that loads (listed with description)
- [ ] Validation rejects a deliberately broken SKILL.md with a named reason"

seed "First real /onboard dogfood — create a live company brain" \
"Run company-onboarding end-to-end with real answers; no invented details.

## Acceptance checks
- [ ] .tex-llm/companies/<slug>/profile.json passes the template's required fields
- [ ] active-company.json points at it; /company reflects it"

seed "Command Deck: wire live events (hooks -> tex-events.jsonl -> SSE feed)" \
"Phase 2 of runpacks/tex-llm-dashboard-design.md — the agentic leap.

## Acceptance checks
- [ ] A REAL hook event (not mocked) appears in the browser feed
- [ ] Terminal-not-live state renders when no session is running"

seed "tex-web: run the Grok web+brand runpack build" \
"Execute runpacks/grok-tex-web-brand-builder.md on the other computer (Grok terminal).

## Acceptance checks
- [ ] Marketing site + app shell build clean; mock data flows only through lib/data.ts
- [ ] Reference project treated read-only (no writes into it)"

seed "SaaS platform spec: auth + credits metering + BYOK vault (private repo)" \
"Spec-only issue: architecture doc for the managed platform (two tiers: credits / BYOK).

## Acceptance checks
- [ ] Doc covers auth, metering proxy, key vault, Stripe, tenant isolation
- [ ] License decision recorded (source-available vs OSS) with rationale"

seed "Linear <-> n8n automation live (gateway + events webhooks)" \
"Import templates/n8n/*.workflow.json on tl-n8n, set TEX_GATEWAY_TOKEN, store Linear key as n8n credential.

## Acceptance checks
- [ ] Gateway roundtrip: curl -> commentCreate -> comment visible on THIS issue
- [ ] Wrong token -> 401 (verified)
- [ ] Linear key exists only as n8n credential (not in git, not on dev machines)"

seed "Fleet: identify aidata + europe-server (server-identity-builder)" \
"Two undocumented tailnet boxes verified reachable 2026-07-22 (aidata.robeul.server, vmi3445423).

## Acceptance checks
- [ ] IDENTITY.md per box in the Host server's folder (read-only sweep)
- [ ] fleet-registry.json roles updated from 'unknown'"

echo
echo "Bootstrap complete. Board: open the T-Ex LLM project in Linear."
