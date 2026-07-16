"""TDD tests for the Arion agent execution engine (App Dev track, Phase 3).

Authored RED-first against a non-existent ``core.engine`` module, then the
engine was implemented until green.
"""

from __future__ import annotations

import unittest

from core.engine import ExecutionEngine, ExecutionResult, UnknownWorkspaceError
from core.router import RouteMatch

AGENTS_WS = "App Dev and Engineering Team/agents"


def make_match(workspace: str = AGENTS_WS, kws=("agent",)) -> RouteMatch:
    return RouteMatch(
        route_name="agent-engineering",
        track="App Dev and Engineering Team",
        workspace=workspace,
        description="",
        score=len(kws),
        matched_keywords=tuple(kws),
        is_default=False,
    )


class EngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ExecutionEngine()

    def test_dispatch_to_registered_handler(self) -> None:
        self.engine.register(AGENTS_WS, lambda q, r: f"handled: {q}", name="echo")
        result = self.engine.dispatch(make_match(), "build an agent")
        self.assertIsInstance(result, ExecutionResult)
        self.assertEqual(result.output, "handled: build an agent")
        self.assertEqual(result.handler, "echo")
        self.assertEqual(result.workspace, AGENTS_WS)

    def test_unknown_workspace_raises(self) -> None:
        with self.assertRaises(UnknownWorkspaceError):
            self.engine.dispatch(make_match(workspace="nope/here"), "x")

    def test_has_workspace(self) -> None:
        self.assertFalse(self.engine.has(AGENTS_WS))
        self.engine.register(AGENTS_WS, lambda q, r: "ok")
        self.assertTrue(self.engine.has(AGENTS_WS))

    def test_result_carries_route_metadata(self) -> None:
        self.engine.register(AGENTS_WS, lambda q, r: "ok")
        result = self.engine.dispatch(
            make_match(kws=("agent", "execution engine")), "x"
        )
        self.assertEqual(result.matched_keywords, ("agent", "execution engine"))
        self.assertEqual(result.route_name, "agent-engineering")

    def test_duplicate_registration_raises(self) -> None:
        self.engine.register(AGENTS_WS, lambda q, r: "a")
        with self.assertRaises(ValueError):
            self.engine.register(AGENTS_WS, lambda q, r: "b")

    def test_handler_name_defaults_to_callable_name(self) -> None:
        def my_handler(q, r):
            return "ok"

        self.engine.register(AGENTS_WS, my_handler)
        result = self.engine.dispatch(make_match(), "x")
        self.assertEqual(result.handler, "my_handler")


if __name__ == "__main__":
    unittest.main(verbosity=2)
