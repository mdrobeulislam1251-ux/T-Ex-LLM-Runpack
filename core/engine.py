"""Arion agent execution engine (App Dev & Engineering track).

The engine owns a registry of *handlers* keyed by workspace path. Given a
``RouteMatch`` produced by :mod:`core.router`, it dispatches the query to the
handler that owns that workspace and wraps the return value in an
:class:`ExecutionResult`.

Handlers are plain callables ``(query: str, route: RouteMatch) -> str``, so a
sub-agent can be a lambda, a function, or any object implementing ``__call__``.
This keeps the engine dependency-free and trivially testable while leaving room
for richer handlers (loaded from the space-named workspace folders) later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from core.router import Router, RouteMatch

Handler = Callable[[str, RouteMatch], str]


class UnknownWorkspaceError(KeyError):
    """Raised when a RouteMatch targets a workspace with no handler."""


@dataclass(frozen=True)
class ExecutionResult:
    """The outcome of dispatching one query to one handler."""

    workspace: str
    route_name: str
    handler: str
    output: str
    matched_keywords: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "workspace": self.workspace,
            "route_name": self.route_name,
            "handler": self.handler,
            "output": self.output,
            "matched_keywords": list(self.matched_keywords),
        }


class ExecutionEngine:
    """Dispatches routed queries to workspace-owned handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, tuple[str, Handler]] = {}

    def register(
        self, workspace: str, handler: Handler, *, name: str | None = None
    ) -> "ExecutionEngine":
        """Register *handler* for *workspace*.

        Raises ``ValueError`` on a duplicate workspace so misconfigured
        double-registration fails loudly instead of silently shadowing.
        """

        if workspace in self._handlers:
            raise ValueError(f"workspace already has a handler: {workspace}")
        resolved_name = name or getattr(handler, "__name__", "handler")
        self._handlers[workspace] = (resolved_name, handler)
        return self

    def has(self, workspace: str) -> bool:
        return workspace in self._handlers

    def dispatch(self, route: RouteMatch, query: str) -> ExecutionResult:
        entry = self._handlers.get(route.workspace)
        if entry is None:
            raise UnknownWorkspaceError(route.workspace)
        handler_name, handler = entry
        output = handler(query, route)
        return ExecutionResult(
            workspace=route.workspace,
            route_name=route.route_name,
            handler=handler_name,
            output=str(output),
            matched_keywords=route.matched_keywords,
        )

    def workspaces(self) -> list[str]:
        return list(self._handlers)


def _acknowledger(query: str, route: RouteMatch) -> str:
    """Default handler: acknowledges receipt and echoes the routing decision.

    A real sub-agent replaces this; it exists so the pipeline is runnable
    end-to-end (via ``arion.py exec``) before domain handlers are written.
    """

    where = "default inbox" if route.is_default else route.route_name
    triggers = ", ".join(route.matched_keywords) or "(fallback)"
    return f"[{where}] acknowledged: '{query}' (triggers: {triggers})"


def build_acknowledger_engine(router: Router) -> ExecutionEngine:
    """Build an engine with an acknowledger registered for every workspace.

    Wires one handler per configured route plus the default route, so any
    query the router can produce has a handler to land on.
    """

    engine = ExecutionEngine()
    seen: set[str] = set()
    for route in router.routes():
        if route.workspace not in seen:
            engine.register(route.workspace, _acknowledger, name="acknowledger")
            seen.add(route.workspace)
    default_ws = router.default.workspace
    if default_ws not in seen:
        engine.register(default_ws, _acknowledger, name="acknowledger")
    return engine
