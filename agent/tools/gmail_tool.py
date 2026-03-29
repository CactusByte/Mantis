from __future__ import annotations

import base64
from email.message import EmailMessage

import requests as req

from ..config import Settings
from .base import AgentTool, ToolContext
from .google_auth import google_access_token


class GmailTool(AgentTool):
    name = "gmail"

    def is_ready(self, settings: Settings) -> bool:
        return bool(
            settings.google_client_id
            and settings.google_client_secret
            and settings.google_refresh_token
        )

    def spec(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "Gmail API (same OAuth as google_calendar). "
                "ops: list_messages, get_message, send_simple."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "op": {
                        "type": "string",
                        "enum": ["list_messages", "get_message", "send_simple"],
                    },
                    "query": {
                        "type": "string",
                        "description": "Gmail search query for list_messages (optional).",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "For list_messages, default 10.",
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Required for get_message.",
                    },
                    "to": {"type": "string", "description": "For send_simple."},
                    "subject": {"type": "string", "description": "For send_simple."},
                    "body": {"type": "string", "description": "Plain text body for send_simple."},
                },
                "required": ["op"],
            },
        }

    def run(self, settings: Settings, params: dict, ctx: ToolContext) -> str:
        token = google_access_token(settings, ctx)
        if not token:
            return (
                "ERROR: Google OAuth not configured. "
                "Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN."
            )
        op = params.get("op")
        headers = {"Authorization": f"Bearer {token}"}
        base = "https://gmail.googleapis.com/gmail/v1/users/me"

        try:
            if op == "list_messages":
                q = params.get("query") or ""
                max_results = int(params.get("max_results") or 10)
                r = req.get(
                    f"{base}/messages",
                    headers=headers,
                    params={"q": q, "maxResults": max(min(max_results, 50), 1)},
                    timeout=20,
                )
                return f"list_messages -> {r.status_code}: {r.text[:2500]}"

            if op == "get_message":
                mid = params.get("message_id")
                if not mid:
                    return "ERROR: message_id required for get_message."
                r = req.get(
                    f"{base}/messages/{mid}",
                    headers=headers,
                    params={"format": "full"},
                    timeout=20,
                )
                return f"get_message -> {r.status_code}: {r.text[:4000]}"

            if op == "send_simple":
                to = params.get("to")
                subject = params.get("subject", "")
                body = params.get("body", "")
                if not to:
                    return "ERROR: to required for send_simple."
                msg = EmailMessage()
                msg["To"] = to
                msg["Subject"] = subject
                msg.set_content(body)
                raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
                r = req.post(
                    f"{base}/messages/send",
                    headers={**headers, "Content-Type": "application/json"},
                    json={"raw": raw},
                    timeout=30,
                )
                return f"send_simple -> {r.status_code}: {r.text[:1500]}"

            return f"ERROR: unknown op: {op}"
        except Exception as exc:
            return f"Gmail API error: {exc}"
