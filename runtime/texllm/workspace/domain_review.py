"""Domain / website review → ideas → brains & skills suggestions."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from texllm.providers import get_provider
from texllm.providers.base import ChatMessage
from texllm.workspace.db import WorkspaceDB, get_workspace


def _fetch_text(url: str, timeout: float = 15.0) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    headers = {"User-Agent": "T-ex-LLM-DomainReview/0.1"}
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        html = resp.text
    # strip tags roughly
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:12000]


def _parse_json_block(raw: str) -> Dict[str, Any]:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return {
        "ideas": [
            {
                "title": "Review draft",
                "summary": raw[:800],
                "team_slug": "ceo",
            }
        ],
        "brains": [],
        "skills": [],
    }


def review_domain(
    domain_or_url: str,
    *,
    notes: str = "",
    db: Optional[WorkspaceDB] = None,
) -> Dict[str, Any]:
    """
    Fetch public site text (best-effort), ask Claude/provider for team ideas,
    brains, and skills; persist to shared workspace DB.
    """
    db = db or get_workspace()
    url = domain_or_url.strip()
    parsed = urlparse(url if "://" in url else f"https://{url}")
    domain = parsed.netloc or parsed.path.split("/")[0]

    fetch_error = None
    site_text = ""
    try:
        site_text = _fetch_text(url if "://" in url else f"https://{domain}")
    except Exception as exc:  # noqa: BLE001
        fetch_error = str(exc)
        site_text = f"(Could not fetch site: {exc})"

    teams = ", ".join(t["slug"] for t in db.list_teams())
    prompt = f"""You are T-ex workspace architect.
Domain: {domain}
URL: {url}
Extra notes: {notes or "none"}
Site excerpt:
{site_text[:8000]}

Propose agentic workspace packages for teams among: {teams}

Return JSON only:
{{
  "overview": "one paragraph",
  "ideas": [{{"title":"","summary":"","team_slug":"ops|sales|dev|tech|ceo|fulfillment|personal-bd"}}],
  "brains": [{{"name":"","role":"","team_slug":"","prompt":""}}],
  "skills": [{{"name":"","description":"","team_slug":"","body":""}}]
}}
Include at least 5 ideas, 3 brains, 3 skills. Prefer concrete product/ops/sales actions.
"""
    provider = get_provider()
    result = provider.complete(
        [
            ChatMessage(
                role="system",
                content="You design multi-team AI agent workspaces. Output valid JSON only.",
            ),
            ChatMessage(role="user", content=prompt),
        ],
        temperature=0.4,
        max_tokens=2500,
    )
    data = _parse_json_block(result.content)

    saved_ideas: List[Dict[str, Any]] = []
    for idea in data.get("ideas") or []:
        if not isinstance(idea, dict):
            continue
        title = str(idea.get("title") or "Untitled idea")
        saved = db.add_idea(
            title=title,
            summary=str(idea.get("summary") or ""),
            domain=domain,
            url=url if "://" in url else f"https://{domain}",
            team_slug=str(idea.get("team_slug") or "ceo"),
            payload=idea,
            source="domain_review",
        )
        saved_ideas.append(saved)

    saved_brains = []
    for b in data.get("brains") or []:
        if not isinstance(b, dict):
            continue
        team = db.get_team(str(b.get("team_slug") or "dev"))
        if not team:
            continue
        br = db.add_brain(
            team["id"],
            name=str(b.get("name") or "Brain"),
            role=str(b.get("role") or "specialist"),
            prompt=str(b.get("prompt") or ""),
        )
        saved_brains.append(br)

    saved_skills = []
    for s in data.get("skills") or []:
        if not isinstance(s, dict):
            continue
        team = db.get_team(str(s.get("team_slug") or "dev"))
        sk = db.add_skill(
            name=str(s.get("name") or "Skill"),
            description=str(s.get("description") or ""),
            body=str(s.get("body") or ""),
            team_id=team["id"] if team else None,
            path=f"workspace/{s.get('team_slug')}/{s.get('name')}",
        )
        saved_skills.append(sk)

    db.log_activity(
        None,
        "domain_review",
        f"Domain review: {domain}",
        f"ideas={len(saved_ideas)} brains={len(saved_brains)} skills={len(saved_skills)}",
    )

    return {
        "domain": domain,
        "url": url if "://" in url else f"https://{domain}",
        "fetch_error": fetch_error,
        "overview": data.get("overview") or "",
        "provider": result.provider,
        "ideas": saved_ideas,
        "brains": saved_brains,
        "skills": saved_skills,
    }
