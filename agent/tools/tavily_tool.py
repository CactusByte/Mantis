from __future__ import annotations

import requests as req

from ..config import Settings
from .base import AgentTool, ToolContext


class TavilySearchTool(AgentTool):
    name = "tavily_search"

    def is_ready(self, settings: Settings) -> bool:
        return bool(settings.tavily_api_key)

    def spec(self) -> dict:
        return {
            "name": self.name,
            "description": "Web search via Tavily API.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "search_depth": {
                        "type": "string",
                        "enum": ["basic", "advanced"],
                        "description": "Optional.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Optional, default 5.",
                    },
                },
                "required": ["query"],
            },
        }

    def run(self, settings: Settings, params: dict, ctx: ToolContext) -> str:
        key = settings.tavily_api_key
        if not key:
            return "ERROR: Set TAVILY_API_KEY."
        query = (params.get("query") or "").strip()
        if not query:
            return "ERROR: query required."
        body: dict = {
            "api_key": key,
            "query": query,
            "max_results": int(params.get("max_results") or 5),
        }
        if params.get("search_depth"):
            body["search_depth"] = params["search_depth"]
        try:
            r = req.post(
                "https://api.tavily.com/search",
                json=body,
                timeout=30,
            )
            return f"tavily_search -> {r.status_code}: {r.text[:8000]}"
        except Exception as exc:
            return f"Tavily error: {exc}"
