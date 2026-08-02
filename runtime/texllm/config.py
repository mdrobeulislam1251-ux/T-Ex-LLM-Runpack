"""Environment-driven settings (model-agnostic)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Model provider (OpenAI-compatible) — optional; local CLI agents need no key
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    # "auto" | "mock" | "openai"
    llm_provider: str = "auto"

    # Public bind (default 3006 — overridable at setup)
    host_port: int = 3006
    host_bind: str = "0.0.0.0"
    host_api_key: str = "change-me"
    log_level: str = "info"

    # Serve built web UI from the same process when true
    serve_web: bool = True
    web_dist_dir: Path = Path("apps/web/dist")

    # Local CLI agent spawn
    allow_local_cli: bool = True
    local_cli_timeout_sec: int = 180
    local_cli_cwd: Path = Path(".")

    # Workers
    worker_concurrency: int = 4
    job_max_iterations: int = 12
    job_max_cost_usd: float = 1.0

    # Code-mode executor (headless coding agent doing real file work)
    code_agent_bin: str = "claude"
    code_agent_timeout_sec: int = 900
    code_agent_allowed_tools: str = "Read,Edit,Write,Grep,Glob,Bash"
    code_runs_dir: Path = Path(".texllm/runs")
    code_diff_max_bytes: int = 200_000

    # Paths
    firmware_dir: Path = Path("firmware")
    repo_root: Path = Path(".")

    def resolve_provider(self) -> str:
        if self.llm_provider != "auto":
            return self.llm_provider
        if self.llm_api_key.strip():
            return "openai"
        return "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()
