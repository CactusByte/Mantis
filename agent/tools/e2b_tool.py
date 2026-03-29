from __future__ import annotations

import importlib.util

from ..config import Settings
from .base import AgentTool, ToolContext


def _e2b_available() -> bool:
    return importlib.util.find_spec("e2b_code_interpreter") is not None


class E2BCodeTool(AgentTool):
    name = "e2b_run"

    def is_ready(self, settings: Settings) -> bool:
        return bool(settings.e2b_api_key) and _e2b_available()

    def spec(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "Run Python code in an ephemeral E2B code interpreter sandbox. "
                "Requires e2b-code-interpreter package and E2B_API_KEY."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python source to execute.",
                    },
                },
                "required": ["code"],
            },
        }

    def run(self, settings: Settings, params: dict, ctx: ToolContext) -> str:
        if not settings.e2b_api_key:
            return "ERROR: Set E2B_API_KEY."
        if not _e2b_available():
            return "ERROR: pip install e2b-code-interpreter"
        code = params.get("code")
        if not code:
            return "ERROR: code required."

        try:
            from e2b_code_interpreter import Sandbox
        except ImportError as exc:
            return f"ERROR: e2b_code_interpreter import failed: {exc}"

        try:
            with Sandbox.create(api_key=settings.e2b_api_key) as sandbox:
                execution = sandbox.run_code(code)
            parts: list[str] = []
            logs = execution.logs
            if logs.stdout:
                parts.append("".join(logs.stdout))
            if logs.stderr:
                parts.append("stderr:\n" + "".join(logs.stderr))
            for res in execution.results or []:
                if getattr(res, "text", None):
                    parts.append(res.text)
                elif getattr(res, "markdown", None):
                    parts.append(res.markdown)
            if execution.error:
                parts.append(f"error: {execution.error}")
            out = "\n".join(parts) if parts else "(no output)"
            return out[:12000]
        except Exception as exc:
            return f"E2B error: {exc}"
