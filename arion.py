#!/usr/bin/env python3
"""Arion — Global Workspace Assistant CLI.

Command-line entrypoint for the keyword-triggered routing system. Given a
task query, Arion resolves which sub-agent workspace should own the work.

Usage:
    python3 arion.py route "deploy the agent to the tl-host over tailnet"
    python3 arion.py route "check my gmail and update asana" --json
    python3 arion.py list
    python3 arion.py schema

Exit codes:
    0  success
    1  routing configuration error
    2  bad CLI usage
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure the repo root is importable when run as a script from anywhere.
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.router import Router, RoutingConfigError  # noqa: E402

DEFAULT_CONFIG = REPO_ROOT / "config" / "routing.json"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arion",
        description="Arion Global Workspace Assistant — keyword task router.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help="Path to routing.json (default: config/routing.json).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_route = sub.add_parser("route", help="Route a task query to a workspace.")
    p_route.add_argument("query", help="The natural-language task query.")
    p_route.add_argument(
        "--json", action="store_true", help="Emit the match as JSON."
    )

    sub.add_parser("list", help="List all configured routes.")
    sub.add_parser("schema", help="Print the routing config schema summary.")

    return parser


def _cmd_route(router: Router, query: str, as_json: bool) -> int:
    match = router.route(query)
    if as_json:
        print(json.dumps(match.as_dict(), indent=2))
        return 0

    tag = "DEFAULT (no keyword matched)" if match.is_default else match.route_name
    print(f"Query      : {query}")
    print(f"Route      : {tag}")
    print(f"Track      : {match.track}")
    print(f"Workspace  : {match.workspace}")
    if match.matched_keywords:
        print(f"Triggers   : {', '.join(match.matched_keywords)} (score {match.score})")
    print(f"Rationale  : {match.description}")
    return 0


def _cmd_list(router: Router) -> int:
    print(f"{'ROUTE':<22}{'PRIORITY':<10}WORKSPACE")
    print("-" * 72)
    for route in sorted(router.routes(), key=lambda r: -r.priority):
        print(f"{route.name:<22}{route.priority:<10}{route.workspace}")
    d = router.default
    print("-" * 72)
    print(f"{'(default)':<22}{'-':<10}{d.workspace}")
    return 0


def _cmd_schema(router: Router) -> int:
    tracks: dict[str, list[str]] = {}
    for route in router.routes():
        tracks.setdefault(route.track, []).append(route.workspace)
    print("Arion routing schema — tracks and workspaces:")
    for track, workspaces in tracks.items():
        print(f"\n  {track}/")
        for ws in workspaces:
            leaf = ws.split("/", 1)[-1] if "/" in ws else ws
            print(f"    └─ {leaf}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        router = Router.from_file(args.config)
    except RoutingConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.command == "route":
        return _cmd_route(router, args.query, args.json)
    if args.command == "list":
        return _cmd_list(router)
    if args.command == "schema":
        return _cmd_schema(router)

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
