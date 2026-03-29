from __future__ import annotations

import requests as req

from ..config import Settings
from .base import AgentTool, ToolContext


def normalize_x_query_params(query: dict | None) -> dict:
    if not query:
        return {}
    normalized: dict[str, str | int | float | bool] = {}
    for key, value in query.items():
        if isinstance(value, list):
            normalized[key] = ",".join(str(item) for item in value)
        else:
            normalized[key] = value
    return normalized


def resolve_x_bearer(settings: Settings, ctx: ToolContext, params: dict) -> str | None:
    override = params.get("bearer_token")
    if override:
        return override
    if ctx.x_bearer_cache:
        return ctx.x_bearer_cache
    token = fetch_x_app_bearer_token(settings)
    if token:
        ctx.x_bearer_cache = token
    return token


def fetch_x_app_bearer_token(settings: Settings) -> str | None:
    client_id = settings.x_client_id
    client_secret = settings.x_client_secret
    if not client_id or not client_secret:
        return None
    try:
        response = req.post(
            "https://api.x.com/oauth2/token",
            auth=(client_id, client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
            data={"grant_type": "client_credentials"},
            timeout=20,
        )
        if not response.ok:
            return None
        data = response.json()
        token = data.get("access_token")
        return token if isinstance(token, str) and token else None
    except Exception:
        return None


def resolve_x_oauth2_user(settings: Settings, params: dict) -> str | None:
    return params.get("oauth2_user_token") or settings.x_oauth2_user_token


class XCreatePostTool(AgentTool):
    name = "x_create_post"

    def is_enabled(self, settings: Settings) -> bool:
        return settings.twitter_tool_enabled

    def is_ready(self, settings: Settings) -> bool:
        return bool(settings.x_oauth2_user_token)

    def spec(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "Create or edit an X post via POST /2/tweets. "
                "Uses OAuth2 user-context token."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "payload": {
                        "type": "object",
                        "description": "JSON body for X create/edit post endpoint.",
                    },
                    "oauth2_user_token": {
                        "type": "string",
                        "description": (
                            "Optional override for OAuth2 user token; "
                            "defaults to X_OAUTH2_USER_TOKEN env var."
                        ),
                    },
                },
                "required": ["payload"],
            },
        }

    def run(self, settings: Settings, params: dict, ctx: ToolContext) -> str:
        payload = params.get("payload")
        if not isinstance(payload, dict):
            return "ERROR: payload must be an object."
        user_token = resolve_x_oauth2_user(settings, params)
        if not user_token:
            return (
                "ERROR: Missing OAuth2 user token for posting. "
                "Set X_OAUTH2_USER_TOKEN (or X_USER_ACCESS_TOKEN/X_ACCESS_TOKEN) "
                "or pass oauth2_user_token."
            )
        headers = {"Content-Type": "application/json"}
        headers["Authorization"] = f"Bearer {user_token}"

        try:
            response = req.post(
                "https://api.x.com/2/tweets",
                json=payload,
                headers=headers,
                timeout=20,
            )
            if response.status_code == 403 and "Unsupported Authentication" in response.text:
                return (
                    "ERROR: X API rejected authentication for POST /2/tweets. "
                    "This endpoint requires user-context auth. "
                    "Use a valid OAuth2 user token with tweet.write scope."
                )
            return f"POST /2/tweets (oauth2-user) -> {response.status_code}: {response.text[:1200]}"
        except Exception as exc:
            return f"X API error (create post): {exc}"


class XGetMentionsTool(AgentTool):
    name = "x_get_mentions"

    def is_enabled(self, settings: Settings) -> bool:
        return settings.twitter_tool_enabled

    def is_ready(self, settings: Settings) -> bool:
        return bool(
            settings.x_bearer_token
            or (settings.x_client_id and settings.x_client_secret)
        )

    def spec(self) -> dict:
        return {
            "name": self.name,
            "description": "Get mentions timeline via GET /2/users/{id}/mentions using bearer token.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "X user id, e.g. 2244994945.",
                    },
                    "query": {
                        "type": "object",
                        "description": "Optional query params (max_results, since_id, tweet.fields, etc).",
                    },
                    "bearer_token": {
                        "type": "string",
                        "description": "Optional override for token; defaults to X_BEARER_TOKEN env var.",
                    },
                },
                "required": ["user_id"],
            },
        }

    def run(self, settings: Settings, params: dict, ctx: ToolContext) -> str:
        user_id = str(params.get("user_id", "")).strip()
        if not user_id:
            return "ERROR: user_id is required."
        token = resolve_x_bearer(settings, ctx, params)
        if not token:
            return (
                "ERROR: Missing X bearer token for mentions. "
                "Set X_BEARER_TOKEN, pass bearer_token, or configure "
                "X_CLIENT_ID/X_CLIENT_SECRET for auto token generation."
            )
        headers = {"Authorization": f"Bearer {token}"}
        query = normalize_x_query_params(params.get("query"))
        url = f"https://api.x.com/2/users/{user_id}/mentions"

        try:
            response = req.get(url, headers=headers, params=query, timeout=20)
            return (
                f"GET /2/users/{user_id}/mentions (bearer) "
                f"-> {response.status_code}: {response.text[:1200]}"
            )
        except Exception as exc:
            return f"X API error (get mentions): {exc}"
