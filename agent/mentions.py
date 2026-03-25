import json
import logging
from pathlib import Path

import requests as req

from .config import Settings
from .runner import AgentRunner
from .tools import ToolRunner


def mentions_tick(settings: Settings, runner: AgentRunner, tool_runner: ToolRunner) -> None:
    log = logging.getLogger("agent")
    if not settings.x_user_id:
        log.info("Mentions tick skipped: X_USER_ID is not configured")
        return

    mention = _fetch_latest_unprocessed_mention(settings, tool_runner)
    if not mention:
        log.info("Mentions tick: no new mention to reply to")
        return

    mention_id = mention["id"]
    mention_text = mention.get("text", "")
    author_username = mention.get("author_username")

    try:
        reply_text = runner.draft_mention_reply(mention_text=mention_text, author_username=author_username)
    except Exception as exc:
        log.error(f"Mentions tick: failed to draft reply for {mention_id}: {exc}")
        return

    user_token = tool_runner._resolve_x_oauth2_user_token({})
    if not user_token:
        log.error("Mentions tick: missing OAuth2 user token for posting replies")
        return

    headers = {
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "text": reply_text,
        "reply": {"in_reply_to_tweet_id": mention_id},
    }

    try:
        response = req.post("https://api.x.com/2/tweets", json=payload, headers=headers, timeout=20)
    except Exception as exc:
        log.error(f"Mentions tick: post request failed for {mention_id}: {exc}")
        return

    if response.status_code >= 400:
        log.error(f"Mentions tick: failed to post reply for {mention_id}: {response.status_code} {response.text[:500]}")
        return

    _save_last_replied_mention_id(settings.workspace, mention_id)
    _clear_selected_mention_id_if_matches(settings.workspace, mention_id)
    log.info(f"Mentions tick: replied to mention {mention_id}")


def _fetch_latest_unprocessed_mention(settings: Settings, tool_runner: ToolRunner) -> dict | None:
    token = tool_runner._resolve_x_token({})
    if not token:
        return None

    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "max_results": 10,
        "tweet.fields": "author_id,created_at,text",
        "expansions": "author_id",
        "user.fields": "username",
    }
    url = f"https://api.x.com/2/users/{settings.x_user_id}/mentions"
    response = req.get(url, headers=headers, params=params, timeout=20)
    if response.status_code >= 400:
        return None

    payload = response.json()
    tweets = payload.get("data") or []
    if not tweets:
        return None

    users_by_id = {
        user.get("id"): user.get("username")
        for user in (payload.get("includes", {}).get("users") or [])
        if isinstance(user, dict) and user.get("id")
    }

    last_replied = _load_last_replied_mention_id(settings.workspace)
    selected_id = _load_selected_mention_id(settings.workspace)

    candidates = []
    for tweet in tweets:
        tweet_id = tweet.get("id")
        if not tweet_id:
            continue
        if last_replied and int(tweet_id) <= int(last_replied):
            continue
        candidates.append(tweet)
    if not candidates:
        return None

    selected = None
    if selected_id:
        for tweet in candidates:
            if str(tweet.get("id")) == selected_id:
                selected = tweet
                break

    chosen = selected or max(candidates, key=lambda t: int(t.get("id", "0")))
    author_id = chosen.get("author_id")
    return {
        "id": str(chosen.get("id")),
        "text": chosen.get("text", ""),
        "author_username": users_by_id.get(author_id),
    }


def _state_path(workspace: Path) -> Path:
    return workspace / "mentions_state.json"


def _selected_path(workspace: Path) -> Path:
    return workspace / "mentions_selected_id.txt"


def _load_last_replied_mention_id(workspace: Path) -> str | None:
    path = _state_path(workspace)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except Exception:
        return None
    last_id = data.get("last_replied_mention_id")
    return str(last_id) if last_id else None


def _save_last_replied_mention_id(workspace: Path, mention_id: str) -> None:
    path = _state_path(workspace)
    path.write_text(json.dumps({"last_replied_mention_id": str(mention_id)}, indent=2))


def _load_selected_mention_id(workspace: Path) -> str | None:
    path = _selected_path(workspace)
    if not path.exists():
        return None
    selected = path.read_text().strip()
    return selected or None


def _clear_selected_mention_id_if_matches(workspace: Path, mention_id: str) -> None:
    path = _selected_path(workspace)
    if not path.exists():
        return
    selected = path.read_text().strip()
    if selected == str(mention_id):
        path.unlink()
