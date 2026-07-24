---
name: orchestration-runpack
description: The company runpack routing table — how the 52 T-Ex LLM agents in 9 teams receive work, who reviews what, and how multi-team projects flow. Use whenever deciding which agent should handle a task or how to sequence a multi-team effort.
---

# Orchestration Runpack — Routing & Review Gates

## Prime rules

1. **No brain, no work.** If `.tex-llm/companies/active-company.json` or the active profile is
   missing, route to the `company-onboarding` skill first. Always.
2. **One owner per task.** Every task has exactly one owning agent and (where required)
   one reviewing agent. Ambiguity goes to ceo-orchestrator.
3. **Gates are hard.** A deliverable whose gate hasn't passed does not ship, merge, or
   get announced. No exceptions for speed.

## Routing table

| Request looks like | Owning agent | Review gate |
|---|---|---|
| Multi-team / unclear ownership / kickoff | ceo-orchestrator | — |
| Product requirements, MVP scope, roadmap | cpo | ceo-orchestrator |
| Delivery planning, process, schedules | coo | — |
| Feature implementation plan | engineering-manager | cto (if architectural) |
| Any-language / cross-stack implementation | fullstack-polyglot | engineering-manager |
| UI implementation | frontend-engineer | design-system-engineer |
| Product dashboards / analytics views | frontend-engineer | design-director (`dashboard-design`) |
| Server/API implementation | backend-engineer | api-engineer (contract) |
| Mobile feature | mobile-engineer | engineering-manager |
| API contract design | api-engineer | cto (breaking changes) |
| **Data table schema, ETL, n8n data tables** | **data-engineer** | **cto (MANDATORY)** |
| Query tuning, migrations execution, backups | database-engineer | cto (prod migrations) |
| CI/CD, Docker, IaC, environments | devops-engineer | — |
| Multi-server SSH fleet, connect/route/identity docs | fleet-manager | cto (state-changing fleet ops) |
| Host/deploy an app on a fleet box + expose it (proxy/tunnel/TLS) | fleet-manager | cto (production expose) |
| Agent environment setup (MCPs, Context7, git identity, SSH aliases) | fleet-manager | — |
| Monitoring, alerts, incidents (ops) | sre-engineer | — |
| Security review, auth hardening | security-engineer | cto |
| Performance issues, load testing | performance-engineer | — |
| Design direction / any design kickoff | design-director | — |
| User research, UX audits | ux-researcher | design-director |
| Flows, wireframes, IA | ux-designer | design-director |
| High-fidelity screens | ui-designer | design-director |
| Tokens, component library, design-code parity | design-system-engineer | design-director |
| Brand identity, brand compliance | brand-designer | design-director |
| Animation, micro-interactions | motion-designer | design-director |
| AI feature planning, model choice | ai-lead | cto (cost/arch) |
| AI feature implementation | ai-developer | ai-eval-engineer |
| Prompt writing / fixing | prompt-engineer | ai-eval-engineer |
| Classical ML, embeddings, fine-tuning | ml-engineer | ai-lead |
| RAG / knowledge search | rag-engineer | ai-eval-engineer |
| AI quality evals | ai-eval-engineer | — |
| ANY bug/error/incident report | triage-lead | — |
| Reproducible bug fixing | bug-hunter | regression-tester |
| S1 production emergency | hotfix-engineer | root-cause-analyst (after) |
| Post-fix verification | regression-tester | — |
| Recurring/systemic failures | root-cause-analyst | cto |
| System architecture design | solutions-architect | cto (MANDATORY) |
| **n8n workflows, webhooks, integrations** | **integration-engineer** | engineering-manager |
| Cloud resources, cost | cloud-engineer | cto (over budget threshold) |
| Dev tooling, scaffolding, monorepo | platform-engineer | — |
| Test strategy, E2E suites | qa-automation-engineer | — |
| Docs, READMEs, runbooks | technical-writer | owning team lead |
| Positioning, campaigns, launches | marketing-director | ceo-orchestrator |
| Copy, blogs, landing pages | content-strategist | marketing-director |
| SEO | seo-specialist | marketing-director |
| Social media | social-media-manager | marketing-director |
| Email marketing | email-marketing-specialist | marketing-director |
| Sales strategy, pricing, playbooks | sales-director | ceo-orchestrator |
| Outbound, lead gen | sales-development-rep | sales-director |
| Outbound engine slot wiring (List / Mailbox / Track tool choice) | sales-director | cto (credential-adjacent) |
| Demos, proposals, deals | account-executive | sales-director |
| Onboarding journeys, retention | customer-success-manager | sales-director |
| Research questions, verification sweeps | research-lead | — |
| Market sizing, competitor analysis | market-analyst | research-lead |
| Opportunity/differentiation strategy | product-strategist | cpo |

## Standard pipelines

**New product / big feature**
research-lead → product-strategist → cpo (PRD) → solutions-architect + cto (architecture)
→ data-engineer → cto (schema gate) → design pipeline → engineering-manager (build plan)
→ engineers implement → qa-automation-engineer + regression-tester → devops-engineer
(ship) → technical-writer (docs) → marketing pipeline (launch)

**Design pipeline**
design-director (direction) → ux-researcher → ux-designer (flows) → ui-designer (screens)
→ motion-designer (motion spec) → design-director (review gate) → design-system-engineer
(tokens/handoff) → frontend-engineer

**Issue pipeline**
triage-lead (reproduce + severity) → S1: hotfix-engineer / S2: bug-hunter →
regression-tester (verify + permanent test) → root-cause-analyst (if systemic) →
sre-engineer (postmortem when production was hit)

**Launch pipeline**
marketing-director (brief) → content-strategist + seo-specialist + social-media-manager
+ email-marketing-specialist (deliverables) → brand-designer (compliance) →
marketing-director (review) → publish

## Team skill libraries (deep doctrine — load before work)

Agent files are personas and routing; SKILLS carry the operational doctrine (exact
commands, verbatim error→fix tables, numeric gates). Before working, the owning agent
loads its team's skills:

| Team / role | Skills |
|---|---|
| Everyone (behavior core) | `environment-recon`, `execution-discipline`, `verification-gates`, `project-bootstrap` |
| Engineering — web/API | `api-design`, `fullstack-delivery`, `systematic-debugging`, `postgres-patterns`, `app-security` |
| Engineering — native apps | `native-app-delivery`, then the platform skill: `android-dev` / `ios-dev` / `macos-dev` / `windows-dev` / `linux-dev` / `harmony-dev`, or `avalonia-dev` for one-codebase cross-platform desktop |
| Design | `ui-ux-design`, `design-core`, `dashboard-design` |
| Data | `data-schema-design`, `data-pipelines`, `sql-analytics`, `supabase-platform`, `clickhouse-analytics`, `elasticsearch-opensearch` |
| DevOps / SRE / Cloud | `docker-operations`, `devops-cicd`, `grafana-observability`, `server-ops-safety`, `network-diagnosis` |
| Fleet / multi-server SSH (fleet-manager) | `server-fleet-management`, `server-identity-builder`, `fleet-app-hosting`, `server-ops-safety`, `network-diagnosis` |
| Environment provisioning (MCPs, Context7, git identity, SSH aliases) | `agent-environment-setup` |
| Security | `app-security`, `server-ops-safety` |
| Issue fixers | `issue-fix-loop`, `systematic-debugging` |
| Marketing | `product-gtm-strategy`; email-marketing-specialist also loads `b2b-outbound-pipeline` (Mailbox-slot deliverability doctrine) |
| Sales | `b2b-outbound-pipeline` (engine slots: List / Mailbox / Track), `product-gtm-strategy` |
| Research & strategy | `research-strategy`, `product-gtm-strategy`, `strategy-workspace` |
| Delivery & PM sync (coo, engineering-manager) | `linear-integration` |

**On-need activation:** teams not named as owner or reviewer of the current task stay
silent — the dev team doesn't wake marketing, marketing doesn't wake the dev team.
One owner, one reviewer, nothing else runs.

## Escalation

- Technical dispute → cto. Product dispute → cpo. Priority dispute → ceo-orchestrator.
- Anything touching credentials or spend beyond the brain's thresholds → cto + user.
- When two agents both plausibly own a task, ceo-orchestrator assigns in one line and
  work proceeds — no ping-pong.
