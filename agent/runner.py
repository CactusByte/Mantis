import logging
from datetime import datetime, timezone

import anthropic

from .config import Settings
from .storage import SessionStore
from .tools import ToolRunner


class AgentRunner:
    def __init__(self, settings: Settings, store: SessionStore, tool_runner: ToolRunner):
        self._settings = settings
        self._store = store
        self._tool_runner = tool_runner
        self._claude = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._log = logging.getLogger("agent")

    def run(self, session_id: str, user_text: str | None = None) -> str | None:
        history = self._store.load_session(session_id)
        system = self._build_system_prompt()

        if user_text:
            history.append({"role": "user", "content": user_text})
        else:
            history.append(
                {
                    "role": "user",
                    "content": (
                        "Heartbeat tick at "
                        f"{datetime.now(timezone.utc).strftime('%H:%M UTC')}. Check your goals."
                    ),
                }
            )

        messages = list(history)
        final_reply = None

        while True:
            tools = self._tool_runner.available_tool_specs()
            response = self._claude.messages.create(
                model=self._settings.model,
                max_tokens=1024,
                system=system,
                tools=tools,
                messages=messages,
            )

            content = [block.model_dump() for block in response.content]
            messages.append({"role": "assistant", "content": content})

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        final_reply = block.text.strip()
                break

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        self._log.info(f"[{session_id}] tool call: {block.name}({block.input})")
                        result = self._tool_runner.run(block.name, block.input)
                        self._log.info(f"[{session_id}] tool result: {result[:80]}")
                        self._store.append_memory(f"[{block.name}] {result[:100]}")
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            }
                        )
                messages.append({"role": "user", "content": tool_results})
                continue

            break

        if user_text:
            self._store.save_session(session_id, messages)

        return final_reply

    def _build_system_prompt(self) -> str:
        soul = self._store.read_text(self._settings.workspace / "SOUL.md")
        heartbeat = self._store.read_text(self._settings.workspace / "HEARTBEAT.md")
        memory = self._store.read_text(self._settings.workspace / "MEMORY.md")
        memory_tail = "\n".join(memory.strip().splitlines()[-20:])

        return f"""{soul}

## Standing goals
{heartbeat}

## Recent memory
{memory_tail}

When you use a tool, wait for the result before replying.
After all tool use is done, write your final reply as plain text.
If this is a heartbeat and nothing needs doing, reply with exactly: HEARTBEAT_OK
"""

    def draft_mention_reply(self, mention_text: str, author_username: str | None = None) -> str:
        prefix = f"@{author_username} " if author_username else ""
        system = (
            "You write concise, friendly replies for X mentions. "
            "Return only the final reply text, no quotes, no markdown. "
            "Keep it under 240 characters."
        )
        user = (
            "Draft a single reply to this mention.\n"
            f"Mention text: {mention_text}\n"
            f"Start with this prefix exactly if provided: {prefix!r}\n"
            "Do not include links unless the mention explicitly asks for one."
        )
        response = self._claude.messages.create(
            model=self._settings.model,
            max_tokens=180,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text = block.text.strip()
                break
        if not text:
            text = f"{prefix}Thanks for the mention."
        if prefix and not text.startswith(prefix):
            text = f"{prefix}{text}"
        return text[:240]
