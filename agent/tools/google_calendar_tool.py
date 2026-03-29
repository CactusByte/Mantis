from __future__ import annotations

import json
from urllib.parse import quote

import requests as req

from ..config import Settings
from .base import AgentTool, ToolContext
from .google_auth import google_access_token


class GoogleCalendarTool(AgentTool):
    name = "google_calendar"

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
                "Google Calendar API (shared OAuth with gmail). "
                "ops: list_events, create_event."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "op": {
                        "type": "string",
                        "enum": ["list_events", "create_event"],
                    },
                    "calendar_id": {
                        "type": "string",
                        "description": "Default primary if omitted.",
                    },
                    "time_min": {
                        "type": "string",
                        "description": "RFC3339, e.g. 2026-03-29T00:00:00Z (list_events).",
                    },
                    "time_max": {
                        "type": "string",
                        "description": "RFC3339 (list_events).",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "list_events, default 20.",
                    },
                    "event": {
                        "type": "object",
                        "description": "Calendar API event resource for create_event (summary, start, end, etc).",
                    },
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
        headers = {"Authorization": f"Bearer {token}"}
        cal_id = params.get("calendar_id") or "primary"
        base = "https://www.googleapis.com/calendar/v3"

        try:
            if params.get("op") == "list_events":
                max_results = int(params.get("max_results") or 20)
                qp = {
                    "singleEvents": "true",
                    "orderBy": "startTime",
                    "maxResults": max(min(max_results, 50), 1),
                }
                if params.get("time_min"):
                    qp["timeMin"] = params["time_min"]
                if params.get("time_max"):
                    qp["timeMax"] = params["time_max"]
                r = req.get(
                    f"{base}/calendars/{quote(cal_id, safe='@')}/events",
                    headers=headers,
                    params=qp,
                    timeout=20,
                )
                return f"list_events -> {r.status_code}: {r.text[:3500]}"

            if params.get("op") == "create_event":
                event = params.get("event")
                if not isinstance(event, dict):
                    return "ERROR: event object required for create_event."
                r = req.post(
                    f"{base}/calendars/{quote(cal_id, safe='@')}/events",
                    headers={**headers, "Content-Type": "application/json"},
                    data=json.dumps(event),
                    timeout=20,
                )
                return f"create_event -> {r.status_code}: {r.text[:2000]}"

            return f"ERROR: unknown op: {params.get('op')}"
        except Exception as exc:
            return f"Calendar API error: {exc}"
