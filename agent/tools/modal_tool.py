from __future__ import annotations

import json

import requests as req

from ..config import Settings
from .base import AgentTool, ToolContext


class ModalWebhookTool(AgentTool):
    name = "modal_webhook"

    def is_ready(self, settings: Settings) -> bool:
        return bool(settings.modal_webhook_url)

    def spec(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "POST a JSON payload to your Modal (or other) HTTPS endpoint. "
                "Set MODAL_WEBHOOK_URL; optional MODAL_WEBHOOK_BEARER for Authorization header."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "payload": {
                        "type": "object",
                        "description": "JSON body to send.",
                    },
                },
                "required": ["payload"],
            },
        }

    def run(self, settings: Settings, params: dict, ctx: ToolContext) -> str:
        url = settings.modal_webhook_url
        if not url:
            return "ERROR: Set MODAL_WEBHOOK_URL."
        payload = params.get("payload")
        if not isinstance(payload, dict):
            return "ERROR: payload must be an object."
        headers = {"Content-Type": "application/json"}
        secret = settings.modal_webhook_bearer
        if secret:
            headers["Authorization"] = f"Bearer {secret}"
        try:
            r = req.post(url, headers=headers, data=json.dumps(payload), timeout=120)
            return f"modal_webhook -> {r.status_code}: {r.text[:6000]}"
        except Exception as exc:
            return f"modal_webhook error: {exc}"
