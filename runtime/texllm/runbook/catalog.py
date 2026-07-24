"""
Pre-loaded full-company runbook: Intent → Product Deployment Agent.

This is the product spine — not a telemetry dashboard.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Ordered company lifecycle. Each phase has placeholder deliverables
# the agent fills when a provider is connected.
RUNBOOK_PHASES: List[Dict[str, Any]] = [
    {
        "id": "intent",
        "order": 1,
        "title": "Intent & Vision",
        "subtitle": "Why this company exists",
        "agent_role": "Vision Agent",
        "status": "ready",  # ready | blocked | running | done
        "placeholder": {
            "company_name": "[Your Company]",
            "one_liner": "[What you sell in one sentence]",
            "problem": "[Pain you solve]",
            "audience": "[Who pays]",
            "success_metric": "[North-star metric]",
        },
        "outputs": [
            "Vision brief",
            "Problem statement",
            "Success criteria",
        ],
        "playbook": "playbooks/runbook/01-intent.md",
    },
    {
        "id": "domain",
        "order": 2,
        "title": "Domain & Market",
        "subtitle": "Website / market review → opportunity map",
        "agent_role": "Market Agent",
        "status": "ready",
        "placeholder": {
            "domain": "[example.com]",
            "competitors": ["[Competitor A]", "[Competitor B]"],
            "positioning": "[How you win]",
            "risks": ["[Risk 1]", "[Risk 2]"],
        },
        "outputs": [
            "Domain review summary",
            "Competitor snapshot",
            "Positioning draft",
        ],
        "playbook": "playbooks/runbook/02-domain.md",
    },
    {
        "id": "product",
        "order": 3,
        "title": "Product Definition",
        "subtitle": "MVP scope, roadmap, agent firmware specs",
        "agent_role": "Product Agent",
        "status": "ready",
        "placeholder": {
            "mvp_features": ["[Feature 1]", "[Feature 2]", "[Feature 3]"],
            "non_goals": ["[Out of scope]"],
            "user_journeys": ["[Journey A]"],
        },
        "outputs": [
            "MVP checklist",
            "User journeys",
            "Firmware package list",
        ],
        "playbook": "playbooks/runbook/03-product.md",
    },
    {
        "id": "teams",
        "order": 4,
        "title": "Team Assembly",
        "subtitle": "Ops · Sales · Dev · Tech · CEO · Fulfillment · Personal BD",
        "agent_role": "Org Agent",
        "status": "ready",
        "placeholder": {
            "teams": [
                "ops",
                "sales",
                "dev",
                "tech",
                "ceo",
                "fulfillment",
                "personal-bd",
            ],
            "brains_per_team": "[Lead + specialists]",
            "skills": "[Playbooks per team]",
        },
        "outputs": [
            "Team map",
            "Brain roster",
            "Skill catalog",
        ],
        "playbook": "playbooks/runbook/04-teams.md",
    },
    {
        "id": "build",
        "order": 5,
        "title": "Build & Agent Firmware",
        "subtitle": "Export brains → versioned agent packages",
        "agent_role": "Build Agent",
        "status": "ready",
        "placeholder": {
            "packages": ["[team]-agents@0.1.0"],
            "eval_suite": "[Golden tasks]",
            "ci": "[Tests green]",
        },
        "outputs": [
            "Firmware packages",
            "Eval results",
            "Release notes draft",
        ],
        "playbook": "playbooks/runbook/05-build.md",
    },
    {
        "id": "gtm",
        "order": 6,
        "title": "Go-to-Market",
        "subtitle": "Sales motion, ops runbooks, fulfillment path",
        "agent_role": "GTM Agent",
        "status": "ready",
        "placeholder": {
            "pricing": "[Plan tiers]",
            "channels": ["[Web]", "[Outbound]", "[Partners]"],
            "onboarding": "[Day-0 checklist]",
        },
        "outputs": [
            "Pricing sketch",
            "Sales sequences",
            "Ops runbooks",
        ],
        "playbook": "playbooks/runbook/06-gtm.md",
    },
    {
        "id": "deploy",
        "order": 7,
        "title": "Product Deployment",
        "subtitle": "Host · port · tailnet · production readiness",
        "agent_role": "Deploy Agent",
        "status": "ready",
        "placeholder": {
            "host": "[0.0.0.0:3006]",
            "auth": "[API keys / OAuth profiles]",
            "access": "[localhost | tailnet | domain]",
            "health": "[/health green]",
        },
        "outputs": [
            "Deploy checklist",
            "Env template",
            "Go-live sign-off",
        ],
        "playbook": "playbooks/runbook/07-deploy.md",
    },
]

PROVIDERS: List[Dict[str, Any]] = [
    {
        "id": "claude",
        "name": "Claude",
        "methods": ["api_key", "setup_token", "local_cli"],
        "hint": "API key sk-ant-… · Max setup-token · claude auth login",
    },
    {
        "id": "openai",
        "name": "ChatGPT / OpenAI",
        "methods": ["api_key", "oauth_codex", "local_cli"],
        "hint": "Platform API key · Codex OAuth · codex CLI",
    },
    {
        "id": "gemini",
        "name": "Gemini",
        "methods": ["api_key", "oauth_google", "local_cli"],
        "hint": "AI Studio key · Google OAuth · gemini CLI",
    },
    {
        "id": "grok",
        "name": "Grok (xAI)",
        "methods": ["api_key"],
        "hint": "xAI API key + base https://api.x.ai/v1",
    },
]


def catalog() -> Dict[str, Any]:
    return {
        "product": "T-ex Company Runbook Agent",
        "tagline": "Intent → teams → firmware → deploy — one agentic company spine",
        "phases": RUNBOOK_PHASES,
        "providers": PROVIDERS,
        "cli": {
            "list": "tex teams",
            "run_phase": 'tex run ceo "Execute runbook phase: intent"',
            "review": "tex review example.com",
            "export": "tex export sales",
            "at": 'tex @T-ex "Start company from intent"',
        },
    }
