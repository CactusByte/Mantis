from __future__ import annotations

import requests as req

from ..config import Settings
from .base import AgentTool, ToolContext


class FirecrawlTool(AgentTool):
    name = "firecrawl_scrape"

    def is_ready(self, settings: Settings) -> bool:
        return bool(settings.firecrawl_api_key)

    def spec(self) -> dict:
        return {
            "name": self.name,
            "description": "Scrape or extract a URL via Firecrawl API (v1 scrape).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "formats": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "e.g. [\"markdown\",\"html\"]. Default [\"markdown\"].",
                    },
                    "only_main_content": {
                        "type": "boolean",
                        "description": "Optional, default true.",
                    },
                },
                "required": ["url"],
            },
        }

    def run(self, settings: Settings, params: dict, ctx: ToolContext) -> str:
        key = settings.firecrawl_api_key
        if not key:
            return "ERROR: Set FIRECRAWL_API_KEY."
        url = params.get("url")
        if not url:
            return "ERROR: url required."
        formats = params.get("formats") or ["markdown"]
        body: dict = {
            "url": url,
            "formats": formats,
        }
        if params.get("only_main_content") is not None:
            body["onlyMainContent"] = bool(params["only_main_content"])
        else:
            body["onlyMainContent"] = True

        try:
            r = req.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=60,
            )
            return f"firecrawl_scrape -> {r.status_code}: {r.text[:8000]}"
        except Exception as exc:
            return f"Firecrawl error: {exc}"
