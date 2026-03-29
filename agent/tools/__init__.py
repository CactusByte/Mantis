"""
Modular agent tools: each tool is a small class (AgentTool).
Add new tools by appending to ALL_TOOLS or passing extra_tools to ToolRunner.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..config import Settings
from .base import AgentTool, ToolContext
from .builtin_file import FileTool
from .builtin_http import HttpTool
from .builtin_x import (
    XCreatePostTool,
    XGetMentionsTool,
    resolve_x_bearer,
    resolve_x_oauth2_user,
)
from .e2b_tool import E2BCodeTool
from .firecrawl_tool import FirecrawlTool
from .gmail_tool import GmailTool
from .google_calendar_tool import GoogleCalendarTool
from .modal_tool import ModalWebhookTool
from .supabase_tool import SupabaseRestTool
from .tavily_tool import TavilySearchTool
from .telegram_tool import TelegramSendTool

ALL_TOOLS: list[AgentTool] = [
    FileTool(),
    HttpTool(),
    XCreatePostTool(),
    XGetMentionsTool(),
    SupabaseRestTool(),
    GmailTool(),
    GoogleCalendarTool(),
    TelegramSendTool(),
    FirecrawlTool(),
    TavilySearchTool(),
    E2BCodeTool(),
    ModalWebhookTool(),
]


class ToolRunner:
    def __init__(
        self,
        settings: Settings,
        *,
        tools: Sequence[AgentTool] | None = None,
    ):
        self._settings = settings
        merged = list(ALL_TOOLS) + list(tools or [])
        self._tools: dict[str, AgentTool] = {}
        for t in merged:
            self._tools[t.name] = t
        self._ctx = ToolContext(
            workspace_root=settings.workspace.resolve(),
            x_bearer_cache=settings.x_bearer_token,
        )

    def run(self, name: str, params: dict) -> str:
        if not self.is_tool_enabled(name):
            return f"ERROR: Tool '{name}' is disabled by configuration."
        if not self.is_tool_ready(name):
            return f"ERROR: Tool '{name}' is not ready (missing required credentials)."
        tool = self._tools.get(name)
        if not tool:
            return f"Unknown tool: {name}"
        return tool.run(self._settings, params, self._ctx)

    def available_tool_specs(self) -> list[dict]:
        return [
            t.spec()
            for t in self._tools.values()
            if self.is_tool_enabled(t.name) and self.is_tool_ready(t.name)
        ]

    def is_tool_enabled(self, name: str) -> bool:
        n = name.strip().lower()
        tool = self._tools.get(n)
        if not tool:
            return False
        if self._settings.enabled_tools and n not in self._settings.enabled_tools:
            return False
        if n in self._settings.disabled_tools:
            return False
        return tool.is_enabled(self._settings)

    def is_tool_ready(self, name: str) -> bool:
        n = name.strip().lower()
        tool = self._tools.get(n)
        if not tool:
            return False
        return tool.is_ready(self._settings)

    def resolve_x_bearer(self, params: dict | None = None) -> str | None:
        return resolve_x_bearer(self._settings, self._ctx, params or {})

    def resolve_x_oauth2_user(self, params: dict | None = None) -> str | None:
        return resolve_x_oauth2_user(self._settings, params or {})
