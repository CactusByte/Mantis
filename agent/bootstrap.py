import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update

from .config import ensure_workspace_files, load_settings
from .heartbeat import heartbeat_tick
from .mentions import mentions_tick
from .runner import AgentRunner
from .storage import SessionStore
from .telegram_channel import create_telegram_app
from .tools import ToolRunner


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    log = logging.getLogger("agent")

    settings = load_settings()
    ensure_workspace_files(settings)

    store = SessionStore(settings)
    tool_runner = ToolRunner(settings)
    runner = AgentRunner(settings, store, tool_runner)

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        heartbeat_tick,
        "interval",
        minutes=settings.heartbeat_minutes,
        next_run_time=datetime.now(timezone.utc),
        args=[runner],
    )
    scheduler.start()
    log.info(f"Heartbeat scheduled every {settings.heartbeat_minutes} min")

    scheduler.add_job(
        mentions_tick,
        "interval",
        minutes=settings.mentions_check_minutes,
        next_run_time=datetime.now(timezone.utc),
        args=[settings, runner, tool_runner],
    )
    log.info(f"Mentions check scheduled every {settings.mentions_check_minutes} min")

    log.info("Agent daemon running. Send a message on Telegram to start.")
    log.info("Press Ctrl+C to stop.")

    app = create_telegram_app(settings, runner)
    try:
        log.info("Telegram adapter started - polling for messages")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        pass
    finally:
        log.info("Shutting down.")
        scheduler.shutdown()
