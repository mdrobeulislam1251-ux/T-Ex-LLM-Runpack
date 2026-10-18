#!/usr/bin/env python3
"""Local demo: run sample-assistant with mock (or real) provider."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

if "LLM_PROVIDER" not in os.environ:
    os.environ["LLM_PROVIDER"] = "mock"

from texllm.config import get_settings
from texllm.schemas import Job
from texllm.workers.runner import TeamRunner


def main() -> int:
    goal = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else "Explain how to integrate T-ex LLM agentic firmware into a SaaS product"
    )
    settings = get_settings()
    settings.firmware_dir = ROOT / "firmware"
    job = Job(
        firmware_id="sample-assistant",
        firmware_version="0.1.0",
        goal=goal,
        input={"goal": goal},
    )
    print(f"Running team job (provider={settings.resolve_provider()})…")
    job = TeamRunner(settings=settings).run_job(job)
    print(json.dumps(json.loads(job.model_dump_json()), indent=2))
    return 0 if job.status.value == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
