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

    # Chat-mode agent sessions: when Claude is connected (setup-token or CLI),
    # the executor stage of chat runs drives a full headless Claude session in
    # the team's memory dir instead of a single-shot completion.
    chat_agent_sessions: bool = True
    chat_agent_allowed_tools: str = "Read,Grep,Glob,Write,Edit"
    team_memory_dir: Path = Path(".texllm/teams")

    # Messaging channels (docs/CHANNELS.md) — secret VALUES live only in .env
    channels_default_team: str = ""  # freeform chat text → draft run here ("" = reply help)
    channels_reply_max_chars: int = 3500  # Telegram hard cap is 4096
    channel_plugins: str = ""  # comma-separated import paths of third-party adapter modules

    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    telegram_allowed_senders: str = ""  # comma-separated numeric user ids
    telegram_api_base: str = "https://api.telegram.org"
    telegram_poll_on_serve: bool = False

    whatsapp_access_token: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_allowed_senders: str = ""  # wa_id digits, e.g. 15551234567
    whatsapp_api_base: str = "https://graph.facebook.com"
    whatsapp_api_version: str = "v21.0"

    google_chat_project_number: str = ""
    google_chat_allowed_senders: str = ""  # users/<id> and/or emails
    google_chat_space_webhook_url: str = ""  # optional incoming-webhook URL for pushes
    google_chat_tokeninfo_url: str = "https://oauth2.googleapis.com/tokeninfo"

    bluebubbles_url: str = ""  # e.g. http://mac-mini.tailnet:1234
    bluebubbles_password: str = ""
    bluebubbles_allowed_senders: str = ""  # +1555… / iMessage emails

    custom_channel_secret: str = ""
    custom_channel_allowed_senders: str = ""

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
