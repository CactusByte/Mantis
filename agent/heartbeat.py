import logging

from .runner import AgentRunner


def heartbeat_tick(runner: AgentRunner) -> None:
    log = logging.getLogger("agent")
    log.info("Heartbeat tick")
    try:
        reply = runner.run("heartbeat", user_text=None)
        if reply and reply != "HEARTBEAT_OK":
            log.info(f"Heartbeat action: {reply[:120]}")
    except Exception as exc:
        log.error(f"Heartbeat error: {exc}")
