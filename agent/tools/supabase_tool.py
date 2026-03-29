from __future__ import annotations

import json

import requests as req

from ..config import Settings
from .base import AgentTool, ToolContext


class SupabaseRestTool(AgentTool):
    name = "supabase_rest"

    def is_ready(self, settings: Settings) -> bool:
        return bool(settings.supabase_url and settings.supabase_service_key)

    def spec(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "Supabase PostgREST: GET/POST/PATCH/DELETE on a table path. "
                "Path is the table name (e.g. todos) or with query (todos?select=*&limit=5)."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PATCH", "DELETE"],
                    },
                    "path": {
                        "type": "string",
                        "description": "Table name and optional ?query string.",
                    },
                    "body": {
                        "type": "object",
                        "description": "JSON body for POST/PATCH.",
                    },
                    "headers_extra": {
                        "type": "object",
                        "description": "Optional extra headers as string key/values.",
                    },
                },
                "required": ["method", "path"],
            },
        }

    def run(self, settings: Settings, params: dict, ctx: ToolContext) -> str:
        base = (settings.supabase_url or "").rstrip("/")
        key = settings.supabase_service_key
        if not base or not key:
            return "ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY)."

        method = params["method"].upper()
        path = str(params["path"]).lstrip("/")
        url = f"{base}/rest/v1/{path}"
        hdrs = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        extra = params.get("headers_extra") or {}
        if isinstance(extra, dict):
            for k, v in extra.items():
                if isinstance(k, str) and isinstance(v, str):
                    hdrs[k] = v

        body = params.get("body")
        try:
            if method == "GET":
                r = req.get(url, headers=hdrs, timeout=25)
            elif method == "POST":
                r = req.post(
                    url,
                    headers=hdrs,
                    data=json.dumps(body) if body is not None else None,
                    timeout=25,
                )
            elif method == "PATCH":
                r = req.patch(
                    url,
                    headers=hdrs,
                    data=json.dumps(body) if body is not None else None,
                    timeout=25,
                )
            elif method == "DELETE":
                r = req.delete(url, headers=hdrs, timeout=25)
            else:
                return f"ERROR: unsupported method {method}"
            return f"supabase_rest {method} -> {r.status_code}: {r.text[:3500]}"
        except Exception as exc:
            return f"Supabase error: {exc}"
