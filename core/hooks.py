"""Arion runtime hook layer (App Dev & Engineering track).

The hook layer is the keyword-triggered interception point: an incoming task
query enters :meth:`QueryHook.on_query`, is routed by :mod:`core.router`, and
is dispatched by :mod:`core.engine` — with a :class:`LifecycleChain` running
registered ``pre`` hooks before the body and ``post`` hooks after.

The shared ``context`` dict lets pre-hooks rewrite the query (e.g. normalize
or inject prefixes) before routing, and lets post-hooks observe the
``ExecutionResult`` (logging, metrics, notifications).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from core.engine import ExecutionEngine, ExecutionResult
from core.router import Router

HookFn = Callable[[dict], None]
Body = Callable[[dict], ExecutionResult]


@dataclass
class LifecycleChain:
    """Ordered pre/post hooks run around an execution body."""

    pre: list[HookFn] = field(default_factory=list)
    post: list[HookFn] = field(default_factory=list)

    def add_pre(self, fn: HookFn) -> "LifecycleChain":
        self.pre.append(fn)
        return self

    def add_post(self, fn: HookFn) -> "LifecycleChain":
        self.post.append(fn)
        return self

    def run(self, context: dict, body: Body) -> ExecutionResult:
        for fn in self.pre:
            fn(context)
        result = body(context)
        context["result"] = result
        for fn in self.post:
            fn(context)
        return result


class QueryHook:
    """Routes an incoming query through the engine, wrapped in a lifecycle."""

    def __init__(
        self,
        router: Router,
        engine: ExecutionEngine,
        lifecycle: LifecycleChain | None = None,
    ) -> None:
        self.router = router
        self.engine = engine
        self.lifecycle = lifecycle or LifecycleChain()

    def on_query(self, query: str) -> ExecutionResult:
        context: dict = {"query": query}

        def body(ctx: dict) -> ExecutionResult:
            # Route AFTER pre-hooks so a pre-hook can rewrite ctx["query"].
            match = self.router.route(ctx["query"])
            ctx["route"] = match
            return self.engine.dispatch(match, ctx["query"])

        return self.lifecycle.run(context, body)
