import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _parse_csv_set(value: str | None) -> set[str]:
    if not value:
        return set()
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    telegram_bot_token: str
    telegram_default_chat_id: str | None
    allowed_users: set[str]
    heartbeat_minutes: int
    workspace: Path
    sessions_dir: Path
    model: str
    x_bearer_token: str | None
    x_oauth2_user_token: str | None
    x_client_id: str | None
    x_client_secret: str | None
    x_user_id: str | None
    mentions_check_minutes: int
    enabled_tools: set[str]
    disabled_tools: set[str]
    twitter_tool_enabled: bool
    supabase_url: str | None
    supabase_service_key: str | None
    google_client_id: str | None
    google_client_secret: str | None
    google_refresh_token: str | None
    firecrawl_api_key: str | None
    tavily_api_key: str | None
    e2b_api_key: str | None
    modal_webhook_url: str | None
    modal_webhook_bearer: str | None


def load_settings() -> Settings:
    load_dotenv()

    workspace = Path("workspace")
    sessions_dir = workspace / "sessions"

    raw_users = os.environ.get("TELEGRAM_ALLOWED_USERS", "")
    allowed_users = {u.strip() for u in raw_users.split(",") if u.strip()}

    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get(
        "SUPABASE_ANON_KEY"
    )

    return Settings(
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        telegram_default_chat_id=os.environ.get("TELEGRAM_DEFAULT_CHAT_ID"),
        allowed_users=allowed_users,
        heartbeat_minutes=int(os.environ.get("HEARTBEAT_MINUTES", 30)),
        workspace=workspace,
        sessions_dir=sessions_dir,
        model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        x_bearer_token=os.environ.get("X_BEARER_TOKEN"),
        x_oauth2_user_token=(
            os.environ.get("X_OAUTH2_USER_TOKEN")
            or os.environ.get("X_USER_ACCESS_TOKEN")
            or os.environ.get("X_ACCESS_TOKEN")
        ),
        x_client_id=os.environ.get("X_CLIENT_ID"),
        x_client_secret=os.environ.get("X_CLIENT_SECRET"),
        x_user_id=os.environ.get("X_USER_ID"),
        mentions_check_minutes=int(os.environ.get("MENTIONS_CHECK_MINUTES", 15)),
        enabled_tools=_parse_csv_set(os.environ.get("ENABLED_TOOLS")),
        disabled_tools=_parse_csv_set(os.environ.get("DISABLED_TOOLS")),
        twitter_tool_enabled=_parse_bool(os.environ.get("TWITTER_TOOL"), default=True),
        supabase_url=os.environ.get("SUPABASE_URL"),
        supabase_service_key=supabase_key,
        google_client_id=os.environ.get("GOOGLE_CLIENT_ID"),
        google_client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        google_refresh_token=os.environ.get("GOOGLE_REFRESH_TOKEN"),
        firecrawl_api_key=os.environ.get("FIRECRAWL_API_KEY"),
        tavily_api_key=os.environ.get("TAVILY_API_KEY"),
        e2b_api_key=os.environ.get("E2B_API_KEY"),
        modal_webhook_url=os.environ.get("MODAL_WEBHOOK_URL"),
        modal_webhook_bearer=os.environ.get("MODAL_WEBHOOK_BEARER"),
    )


def ensure_workspace_files(settings: Settings) -> None:
    settings.sessions_dir.mkdir(parents=True, exist_ok=True)
    (settings.workspace / "skills").mkdir(parents=True, exist_ok=True)

    soul_path = settings.workspace / "SOUL.md"
    hb_path = settings.workspace / "HEARTBEAT.md"
    mem_path = settings.workspace / "MEMORY.md"

    if not soul_path.exists():
        soul_path.write_text(
            "# Soul\nYou are a helpful autonomous agent.\n"
            "Be concise. Prefer doing less over doing the wrong thing.\n"
            "When unsure, say so.\n"
        )

    if not hb_path.exists():
        hb_path.write_text(
            "# Heartbeat goals\n"
            "If nothing needs doing, reply with: HEARTBEAT_OK\n\n"
            "## Goals\n"
            "- [ ] Nothing yet - add your standing goals here.\n"
        )

    if not mem_path.exists():
        mem_path.write_text("# Memory\n")
