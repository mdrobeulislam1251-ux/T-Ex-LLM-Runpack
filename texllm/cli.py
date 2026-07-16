"""CLI: run a local team job without the HTTP host."""

from __future__ import annotations

import argparse
import json
import sys

from texllm.config import get_settings
from texllm.schemas import Job
from texllm.workers.runner import TeamRunner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="T-ex LLM team runner CLI")
    parser.add_argument("goal", nargs="?", help="Job goal / user request")
    parser.add_argument(
        "--firmware",
        default="sample-assistant",
        help="Firmware id (default: sample-assistant)",
    )
    parser.add_argument("--version", default="0.1.0", help="Firmware version")
    parser.add_argument(
        "--provider",
        choices=["auto", "mock", "openai"],
        default=None,
        help="Override LLM_PROVIDER",
    )
    parser.add_argument("--json", action="store_true", help="Print full job JSON")
    args = parser.parse_args(argv)

    if not args.goal:
        parser.print_help()
        return 2

    settings = get_settings()
    if args.provider:
        # pydantic settings is frozen via cache — rebuild
        from texllm import config as config_mod

        config_mod.get_settings.cache_clear()
        import os

        os.environ["LLM_PROVIDER"] = args.provider
        settings = get_settings()

    job = Job(
        firmware_id=args.firmware,
        firmware_version=args.version,
        goal=args.goal,
        input={"goal": args.goal},
    )
    runner = TeamRunner(settings=settings)
    job = runner.run_job(job)

    if args.json:
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
