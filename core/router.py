"""Arion keyword-triggered routing engine.

Given a natural-language task query, resolve the sub-agent workspace that
should own it. Matching is deterministic, case-insensitive, and
word-boundary aware so that "email" does not spuriously match "emailing a
teammate about deployments" more strongly than the deployment route.

Stdlib only — no third-party dependencies — so the router runs in any
Python 3.8+ environment without an install step.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


class RoutingConfigError(ValueError):
    """Raised when a routing configuration is structurally invalid."""


@dataclass(frozen=True)
class Route:
    """A single routing rule loaded from the configuration."""

    name: str
    track: str
    workspace: str
    keywords: tuple[str, ...]
    priority: int = 0
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise RoutingConfigError("route is missing a 'name'")
        if not self.workspace:
            raise RoutingConfigError(f"route '{self.name}' is missing a 'workspace'")
        if not self.keywords:
            raise RoutingConfigError(f"route '{self.name}' has no keywords")


@dataclass(frozen=True)
class RouteMatch:
    """The result of routing a query."""

    route_name: str
    track: str
    workspace: str
    description: str
    score: int
    matched_keywords: tuple[str, ...]
    is_default: bool

    def as_dict(self) -> dict:
        return {
            "route_name": self.route_name,
            "track": self.track,
            "workspace": self.workspace,
            "description": self.description,
            "score": self.score,
            "matched_keywords": list(self.matched_keywords),
            "is_default": self.is_default,
        }


def _compile_keyword(keyword: str) -> re.Pattern[str]:
    """Compile a keyword into a case-insensitive, word-boundary pattern.

    Multi-word keywords ("execution engine") tolerate arbitrary internal
    whitespace so "execution   engine" still matches. Hyphens are treated
    literally so "sub-agent" matches "sub-agent" but not "sub agent".
    """

    tokens = keyword.strip().split()
    escaped = r"\s+".join(re.escape(tok) for tok in tokens)
    return re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)


class Router:
    """Routes task queries to sub-agent workspaces via keyword scoring."""

    def __init__(self, routes: Iterable[Route], default_route: RouteMatch) -> None:
        self._routes = list(routes)
        if not self._routes:
            raise RoutingConfigError("router requires at least one route")
        self._default = default_route
        # Pre-compile keyword patterns once; scoring runs hot per query.
        self._patterns: dict[str, list[tuple[str, re.Pattern[str]]]] = {
            route.name: [(kw, _compile_keyword(kw)) for kw in route.keywords]
            for route in self._routes
        }

    @classmethod
    def from_config(cls, config: dict) -> "Router":
        try:
            raw_routes = config["routes"]
            raw_default = config["default_route"]
        except KeyError as exc:  # noqa: TRY003 - explicit message is clearer
            raise RoutingConfigError(f"routing config missing key: {exc}") from exc

        routes = [
            Route(
                name=r["name"],
                track=r["track"],
                workspace=r["workspace"],
                keywords=tuple(r["keywords"]),
                priority=int(r.get("priority", 0)),
                description=r.get("description", ""),
            )
            for r in raw_routes
        ]
        default = RouteMatch(
            route_name=raw_default["name"],
            track=raw_default["track"],
            workspace=raw_default["workspace"],
            description=raw_default.get("description", ""),
            score=0,
            matched_keywords=(),
            is_default=True,
        )
        return cls(routes, default)

    @classmethod
    def from_file(cls, path: str | Path) -> "Router":
        path = Path(path)
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RoutingConfigError(f"routing config not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise RoutingConfigError(f"routing config is not valid JSON: {exc}") from exc
        return cls.from_config(config)

    def _score_route(self, route: Route, query: str) -> tuple[int, list[str]]:
        """Score a single route against the query.

        A keyword's weight is the number of whitespace-delimited tokens it
        contains, so a specific multi-word phrase ("execution engine")
        outranks an incidental single-word hit ("agent").
        """

        score = 0
        matched: list[str] = []
        for keyword, pattern in self._patterns[route.name]:
            if pattern.search(query):
                score += len(keyword.split())
                matched.append(keyword)
        return score, matched

    def route(self, query: str) -> RouteMatch:
        """Return the best-matching workspace for *query*.

        Ties are broken by route priority (higher wins), then by config
        order. When nothing matches, the configured default route is
        returned with ``is_default=True``.
        """

        if not query or not query.strip():
            return self._default

        best: RouteMatch | None = None
        best_key: tuple[int, int, int] | None = None

        for index, route in enumerate(self._routes):
            score, matched = self._score_route(route, query)
            if score == 0:
                continue
            # Sort key: score desc, priority desc, earlier config order.
            key = (score, route.priority, -index)
            if best_key is None or key > best_key:
                best_key = key
                best = RouteMatch(
                    route_name=route.name,
                    track=route.track,
                    workspace=route.workspace,
                    description=route.description,
                    score=score,
                    matched_keywords=tuple(matched),
                    is_default=False,
                )

        return best if best is not None else self._default

    def routes(self) -> list[Route]:
        """Return a copy of the loaded routes (config order preserved)."""

        return list(self._routes)

    @property
    def default(self) -> RouteMatch:
        return self._default
