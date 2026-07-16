"""TDD test suite for the Arion routing engine.

Per the Arion TDD blueprint (see tasks.md), every routing behaviour is
pinned by a test. These tests were authored to fail first against an empty
`core.router` module, then the engine was implemented until they pass.

Run:
    python3 -m pytest tests/ -q
    # or, with no pytest installed:
    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from core.router import Router, RoutingConfigError

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "routing.json"


def build_router() -> Router:
    return Router.from_file(CONFIG_PATH)


class RoutingConfigTests(unittest.TestCase):
    def test_shipping_config_loads(self) -> None:
        router = build_router()
        self.assertGreaterEqual(len(router.routes()), 6)

    def test_missing_keywords_is_rejected(self) -> None:
        bad = {
            "default_route": {
                "name": "d",
                "track": "t",
                "workspace": "t/inbox",
            },
            "routes": [{"name": "x", "track": "t", "workspace": "t/x", "keywords": []}],
        }
        with self.assertRaises(RoutingConfigError):
            Router.from_config(bad)

    def test_missing_default_route_is_rejected(self) -> None:
        with self.assertRaises(RoutingConfigError):
            Router.from_config({"routes": []})


class EngineeringTrackRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = build_router()

    def test_agent_query_routes_to_agents(self) -> None:
        match = self.router.route("build a new sub-agent orchestrator")
        self.assertEqual(match.track, "App Dev and Engineering Team")
        self.assertEqual(match.workspace, "App Dev and Engineering Team/agents")
        self.assertFalse(match.is_default)

    def test_deployment_query_routes_to_deployments(self) -> None:
        match = self.router.route("deploy to the tl-host over tailnet via ssh")
        self.assertEqual(
            match.workspace, "App Dev and Engineering Team/deployments"
        )

    def test_hook_query_routes_to_runtime_hooks(self) -> None:
        match = self.router.route("register a runtime hook on the lifecycle event")
        self.assertEqual(
            match.workspace, "App Dev and Engineering Team/runtime_hooks"
        )


class WorkspaceTrackRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = build_router()

    def test_gmail_query_routes_to_tool_handlers(self) -> None:
        match = self.router.route("read my gmail and file it in asana")
        self.assertEqual(
            match.workspace, "Robeul's Workspace Assistant/tool_handlers"
        )

    def test_task_query_routes_to_tasks(self) -> None:
        match = self.router.route("add this to my sprint backlog roadmap")
        self.assertEqual(match.workspace, "Robeul's Workspace Assistant/tasks")

    def test_support_query_routes_to_pipelines(self) -> None:
        match = self.router.route("set up a support escalation workflow")
        self.assertEqual(
            match.workspace, "Robeul's Workspace Assistant/pipelines"
        )


class ScoringAndFallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = build_router()

    def test_empty_query_returns_default(self) -> None:
        match = self.router.route("   ")
        self.assertTrue(match.is_default)
        self.assertEqual(match.workspace, "Robeul's Workspace Assistant/tasks/inbox")

    def test_unmatched_query_returns_default(self) -> None:
        match = self.router.route("xyzzy plugh nothing here matches")
        self.assertTrue(match.is_default)

    def test_word_boundary_prevents_substring_false_match(self) -> None:
        # "management" contains "agent" as a substring but must NOT trigger
        # the agent route via that substring alone.
        match = self.router.route("management review of quarterly numbers")
        self.assertNotIn("agent", match.matched_keywords)

    def test_multiword_keyword_outscores_incidental_single_word(self) -> None:
        # "execution engine" (2 tokens) should win over a lone "task" hit.
        match = self.router.route("tune the execution engine for this task")
        self.assertEqual(match.workspace, "App Dev and Engineering Team/agents")
        self.assertIn("execution engine", match.matched_keywords)

    def test_matched_keywords_are_reported(self) -> None:
        match = self.router.route("deploy via playwright")
        self.assertTrue(match.matched_keywords)
        self.assertGreater(match.score, 0)


class SchemaIntegrityTests(unittest.TestCase):
    """Guards that config and on-disk folder tree stay in sync."""

    def setUp(self) -> None:
        self.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_every_route_track_is_one_of_two_tracks(self) -> None:
        allowed = {"App Dev and Engineering Team", "Robeul's Workspace Assistant"}
        for route in self.config["routes"]:
            self.assertIn(route["track"], allowed)

    def test_workspace_is_nested_under_its_track(self) -> None:
        for route in self.config["routes"]:
            self.assertTrue(
                route["workspace"].startswith(route["track"] + "/"),
                f"{route['name']} workspace not under its track",
            )

    def test_workspace_folders_exist_on_disk(self) -> None:
        for route in self.config["routes"]:
            path = REPO_ROOT / route["workspace"]
            self.assertTrue(
                path.is_dir(), f"missing workspace folder: {route['workspace']}"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
