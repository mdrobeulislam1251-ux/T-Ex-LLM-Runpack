"""CLI: team jobs, agent detect, serve."""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="texllm",
        description="T-ex LLM — team runners, local CLI agents, host server",
    )
    sub = parser.add_subparsers(dest="cmd")

    # default / run job
    p_run = sub.add_parser("run", help="Run a team job (mock or API provider)")
    p_run.add_argument("goal", nargs="?", help="Job goal")
    p_run.add_argument("--firmware", default="sample-assistant")
    p_run.add_argument("--version", default="0.1.0")
    p_run.add_argument("--provider", choices=["auto", "mock", "openai"], default=None)
    p_run.add_argument("--json", action="store_true")

    sub.add_parser("agents", help="Detect terminal AI CLIs on PATH")

    p_spawn = sub.add_parser("spawn", help="Spawn a local agent CLI with a prompt")
    p_spawn.add_argument("agent_id", help="e.g. claude, codex, gemini")
    p_spawn.add_argument("prompt", help="Prompt text")
    p_spawn.add_argument("--timeout", type=int, default=180)

    p_serve = sub.add_parser("serve", help="Start host + web UI (default port 3006)")
    p_serve.add_argument("--port", type=int, default=None, help="Override HOST_PORT")
    p_serve.add_argument("--host", default=None, help="Bind address (default 0.0.0.0)")
    p_serve.add_argument("--no-web", action="store_true", help="API only")

    # backward compat: texllm "goal" without subcommand
    parser.add_argument("goal_positional", nargs="?", help=argparse.SUPPRESS)
    parser.add_argument("--firmware", default="sample-assistant", help=argparse.SUPPRESS)
    parser.add_argument("--version", default="0.1.0", help=argparse.SUPPRESS)
    parser.add_argument(
        "--provider",
        choices=["auto", "mock", "openai"],
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--json", action="store_true", help=argparse.SUPPRESS)

    args = parser.parse_args(argv)

    # Legacy: python -m texllm.cli "goal"
    if args.cmd is None and (args.goal_positional or argv and not str(argv[0]).startswith("-")):
        goal = args.goal_positional
        if not goal and argv:
            # re-parse as run
            return main(["run", *argv])
        return _cmd_run(
            goal=goal,
            firmware=args.firmware,
            version=args.version,
            provider=args.provider,
            as_json=args.json,
        )

    if args.cmd == "run":
        return _cmd_run(
            goal=args.goal,
            firmware=args.firmware,
            version=args.version,
            provider=args.provider,
            as_json=args.json,
        )
    if args.cmd == "agents":
        from texllm.agents.detect import detect_report

        print(json.dumps(detect_report(), indent=2))
        return 0
    if args.cmd == "spawn":
        from texllm.agents.local_cli import LocalCliError, run_local_agent

        try:
            result = run_local_agent(
                args.agent_id, args.prompt, timeout_sec=args.timeout
            )
        except LocalCliError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1
    if args.cmd == "serve":
        import os

        if args.port is not None:
            os.environ["HOST_PORT"] = str(args.port)
        if args.host:
            os.environ["HOST_BIND"] = args.host
        if args.no_web:
            os.environ["SERVE_WEB"] = "false"
        from texllm import config as config_mod

        config_mod.get_settings.cache_clear()
        from texllm.host.app import main as serve_main

        serve_main()
        return 0

    parser.print_help()
    return 2


def _cmd_run(
    *,
    goal: str | None,
    firmware: str,
    version: str,
    provider: str | None,
    as_json: bool,
) -> int:
    if not goal:
        print("Usage: texllm run \"your goal\"", file=sys.stderr)
        return 2

    if provider:
        import os

        from texllm import config as config_mod

        config_mod.get_settings.cache_clear()
        os.environ["LLM_PROVIDER"] = provider

    from texllm.config import get_settings
    from texllm.schemas import Job
    from texllm.workers.runner import TeamRunner

    settings = get_settings()
    job = Job(
        firmware_id=firmware,
        firmware_version=version,
        goal=goal,
        input={"goal": goal},
    )
    job = TeamRunner(settings=settings).run_job(job)

    if as_json:
        print(job.model_dump_json(indent=2))
    else:
        print(f"status: {job.status.value}")
        if job.error:
            print(f"error: {job.error}")
        if job.result:
            print(f"review_passed: {job.result.review_passed}")
            print(f"iterations: {job.result.iterations}")
            print(f"summary: {job.result.summary}")
            print("output:")
            print(json.dumps(job.result.output, indent=2))
    return 0 if job.status.value == "succeeded" else 1


if __name__ == "__main__":
    sys.exit(main())
