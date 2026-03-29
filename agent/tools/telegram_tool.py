from __future__ import annotations

import requests as req

from ..config import Settings
from .base import AgentTool, ToolContext


class TelegramSendTool(AgentTool):
    name = "telegram_send"

    def is_ready(self, settings: Settings) -> bool:
        return bool(settings.telegram_bot_token)

    def spec(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "Send a Telegram message via Bot API sendMessage. "
                "Uses TELEGRAM_BOT_TOKEN; chat_id defaults to TELEGRAM_DEFAULT_CHAT_ID if set."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "chat_id": {
                        "type": "string",
                        "description": "Target chat id. Optional if TELEGRAM_DEFAULT_CHAT_ID is set.",
                    },
                    "text": {"type": "string"},
                    "parse_mode": {
                        "type": "string",
                        "enum": ["HTML", "Markdown", "MarkdownV2"],
                        "description": "Optional.",
                    },
                },
                "required": ["text"],
            },
        }

    def run(self, settings: Settings, params: dict, ctx: ToolContext) -> str:
        token = settings.telegram_bot_token
        chat_id = params.get("chat_id") or settings.telegram_default_chat_id
        text = params.get("text", "")
        if not chat_id:
            return "ERROR: Provide chat_id or set TELEGRAM_DEFAULT_CHAT_ID."
        payload: dict = {"chat_id": chat_id, "text": text}
        if params.get("parse_mode"):
            payload["parse_mode"] = params["parse_mode"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            r = req.post(url, json=payload, timeout=20)
            return f"telegram_send -> {r.status_code}: {r.text[:1500]}"
        except Exception as exc:
            return f"Telegram error: {exc}"
