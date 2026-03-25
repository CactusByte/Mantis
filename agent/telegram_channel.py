import asyncio
import logging

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from .config import Settings
from .runner import AgentRunner


def create_telegram_app(settings: Settings, runner: AgentRunner):
    log = logging.getLogger("agent")

    async def on_telegram_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        msg = update.message
        username = msg.from_user.username or str(msg.from_user.id)
        text = msg.text or ""

        if settings.allowed_users and username not in settings.allowed_users:
            log.warning(f"Telegram: rejected @{username}")
            await msg.reply_text("Sorry, you're not authorised to use this agent.")
            return

        session_id = f"dm:telegram:{username}"
        log.info(f"[{session_id}] received: {text[:60]}")
        await ctx.bot.send_chat_action(chat_id=msg.chat_id, action="typing")

        loop = asyncio.get_event_loop()
        reply = await loop.run_in_executor(None, runner.run, session_id, text)

        if reply and reply != "HEARTBEAT_OK":
            await msg.reply_text(reply)

    app = ApplicationBuilder().token(settings.telegram_bot_token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_telegram_message))
    return app
