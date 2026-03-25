import json
from datetime import datetime, timezone
from pathlib import Path

from .config import Settings


class SessionStore:
    def __init__(self, settings: Settings):
        self._settings = settings

    def _session_path(self, session_id: str) -> Path:
        return self._settings.sessions_dir / f"{session_id.replace(':', '_')}.json"

    def load_session(self, session_id: str) -> list[dict]:
        path = self._session_path(session_id)
        if path.exists():
            return json.loads(path.read_text()).get("history", [])
        return []

    def save_session(self, session_id: str, history: list[dict]) -> None:
        path = self._session_path(session_id)
        path.write_text(json.dumps({"id": session_id, "history": history}, indent=2))

    def append_memory(self, text: str) -> None:
        mem = self._settings.workspace / "MEMORY.md"
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        with mem.open("a") as f:
            f.write(f"\n- [{ts}] {text}")

    @staticmethod
    def read_text(path: Path) -> str:
        return path.read_text() if path.exists() else ""
