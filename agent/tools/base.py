from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from ..config import Settings


@dataclass
class ToolContext:
    workspace_root: Path
    x_bearer_cache: str | None = None
    _google_access_token: str | None = field(default=None, repr=False)
    _google_access_expiry: float = field(default=0.0, repr=False)

    def google_token_ttl_ok(self) -> bool:
        return bool(self._google_access_token) and time.time() < (self._google_access_expiry - 60)

    def set_google_token(self, token: str, expires_in: int) -> None:
        self._google_access_token = token
        self._google_access_expiry = time.time() + float(expires_in)

    @property
    def google_access_token(self) -> str | None:
        return self._google_access_token


class AgentTool(ABC):
    name: str

    @abstractmethod
    def spec(self) -> dict:
        """Anthropic tool schema: name, description, input_schema."""

    def is_enabled(self, settings: Settings) -> bool:
        return True

    def is_ready(self, settings: Settings) -> bool:
        return True

    @abstractmethod
    def run(self, settings: Settings, params: dict, ctx: ToolContext) -> str:
        pass
