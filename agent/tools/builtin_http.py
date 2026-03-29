from __future__ import annotations

import requests as req

from ..config import Settings
from .base import AgentTool, ToolContext


class HttpTool(AgentTool):
    name = "http"

    def spec(self) -> dict:
        return {
            "name": self.name,
            "description": "Make an HTTP GET or POST request to a URL.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "enum": ["GET", "POST"]},
                    "url": {"type": "string"},
                    "body": {"type": "object", "description": "JSON body for POST"},
                },
                "required": ["method", "url"],
            },
        }

    def run(self, settings: Settings, params: dict, ctx: ToolContext) -> str:
        method = params["method"].upper()
        url = params["url"]
        try:
            if method == "GET":
                response = req.get(url, timeout=15)
            else:
                response = req.post(url, json=params.get("body"), timeout=15)
            return f"{method} {url} -> {response.status_code}: {response.text[:300]}"
        except Exception as exc:
            return f"HTTP error: {exc}"
