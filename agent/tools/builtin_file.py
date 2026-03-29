from __future__ import annotations

from ..config import Settings
from .base import AgentTool, ToolContext


class FileTool(AgentTool):
    name = "file"

    def spec(self) -> dict:
        return {
            "name": self.name,
            "description": "Read or write a file inside workspace/. Use op=read or op=write.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "op": {"type": "string", "enum": ["read", "write", "append"]},
                    "path": {"type": "string", "description": "Path relative to workspace/"},
                    "content": {"type": "string", "description": "Required for write/append"},
                },
                "required": ["op", "path"],
            },
        }

    def run(self, settings: Settings, params: dict, ctx: ToolContext) -> str:
        op = params["op"]
        target = (settings.workspace / params["path"]).resolve()

        if not str(target).startswith(str(ctx.workspace_root)):
            return "ERROR: path outside workspace not allowed"

        if op == "read":
            return target.read_text()[:2000] if target.exists() else "File not found"

        content = params.get("content", "")
        target.parent.mkdir(parents=True, exist_ok=True)

        if op == "write":
            target.write_text(content)
            return f"Written {len(content)} chars to {params['path']}"

        if op == "append":
            with target.open("a") as f:
                f.write(content)
            return f"Appended {len(content)} chars to {params['path']}"

        return f"Unsupported file op: {op}"
