"""TDD tests for the Arion runtime hook layer (App Dev track, Phase 2).

Authored RED-first against a non-existent ``core.hooks`` module. Verifies an
incoming query is routed then dispatched, and that lifecycle pre/post hooks
fire in the correct order around the engine body.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from core.engine import ExecutionEngine, build_acknowledger_engine
from core.hooks import LifecycleChain, QueryHook
from core.router import Router

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG = REPO_ROOT / "config" / "routing.json"


class QueryHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = Router.from_file(CONFIG)
        self.engine = build_acknowledger_engine(self.router)

    def test_query_routes_and_dispatches(self) -> None:
        hook = QueryHook(self.router, self.engine)
        result = hook.on_query("deploy to tl-host over tailnet via ssh")
        self.assertEqual(
            result.workspace, "App Dev and Engineering Team/deployments"
        )
        self.assertIn("tl-host", result.output)

    def test_unmatched_query_dispatches_to_default(self) -> None:
        hook = QueryHook(self.router, self.engine)
        result = hook.on_query("xyzzy nothing matches here")
        self.assertEqual(
            result.workspace, "Robeul's Workspace Assistant/tasks/inbox"
        )


class LifecycleOrderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = Router.from_file(CONFIG)

    def test_pre_runs_before_body_and_post_after(self) -> None:
        order: list[str] = []
        lifecycle = LifecycleChain()
        lifecycle.add_pre(lambda ctx: order.append("pre"))
        lifecycle.add_post(lambda ctx: order.append(f"post:{ctx['result'].route_name}"))

        engine = ExecutionEngine()
        engine.register(
            "App Dev and Engineering Team/agents",
            lambda q, r: (order.append("body"), "done")[1],
        )

        hook = QueryHook(self.router, engine, lifecycle)
        result = hook.on_query("build a sub-agent orchestrator")

        self.assertEqual(order[0], "pre")
        self.assertEqual(order[1], "body")
        self.assertTrue(order[2].startswith("post:"))
        self.assertEqual(result.output, "done")

    def test_pre_hook_can_mutate_context_before_routing(self) -> None:
        lifecycle = LifecycleChain()
        # Pre-hook rewrites the query before it is routed.
        lifecycle.add_pre(lambda ctx: ctx.__setitem__("query", "deploy via ssh"))

        engine = build_acknowledger_engine(self.router)
        hook = QueryHook(self.router, engine, lifecycle)
        result = hook.on_query("this text would otherwise route to inbox")
        self.assertEqual(
            result.workspace, "App Dev and Engineering Team/deployments"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
