import requests as req

from .config import Settings

TOOLS = [
    {
        "name": "file",
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
    },
    {
        "name": "http",
        "description": "Make an HTTP GET or POST request to a URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "method": {"type": "string", "enum": ["GET", "POST"]},
                "url": {"type": "string"},
                "body": {"type": "object", "description": "JSON body for POST"},
            },
            "required": ["method", "url"],
        },
    },
    {
        "name": "x_create_post",
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
    },
    {
        "name": "x_get_mentions",
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
    },
]


class ToolRunner:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._workspace_root = settings.workspace.resolve()
        self._cached_app_bearer_token: str | None = settings.x_bearer_token

    def run(self, name: str, params: dict) -> str:
        if name == "file":
            return self._run_file_tool(params)
        if name == "http":
            return self._run_http_tool(params)
        if name == "x_create_post":
            return self._run_x_create_post_tool(params)
        if name == "x_get_mentions":
            return self._run_x_get_mentions_tool(params)
        return f"Unknown tool: {name}"

    def _run_file_tool(self, params: dict) -> str:
        op = params["op"]
        target = (self._settings.workspace / params["path"]).resolve()

        # Safety: block path traversal outside workspace/
        if not str(target).startswith(str(self._workspace_root)):
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

    @staticmethod
    def _run_http_tool(params: dict) -> str:
        method = params["method"].upper()
        url = params["url"]
        try:
            if method == "GET":
                response = req.get(url, timeout=15)
            else:
                response = req.post(url, json=params.get("body"), timeout=15)
            return f"{method} {url} -> {response.status_code}: {response.text[:300]}"
        except Exception as exc:
            return f"HTTP error: {exc}"

    def _resolve_x_token(self, params: dict) -> str | None:
        override = params.get("bearer_token")
        if override:
            return override
        if self._cached_app_bearer_token:
            return self._cached_app_bearer_token
        token = self._fetch_x_app_bearer_token()
        if token:
            self._cached_app_bearer_token = token
        return token

    def _fetch_x_app_bearer_token(self) -> str | None:
        client_id = self._settings.x_client_id
        client_secret = self._settings.x_client_secret
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

    def _resolve_x_oauth2_user_token(self, params: dict) -> str | None:
        return params.get("oauth2_user_token") or self._settings.x_oauth2_user_token

    @staticmethod
    def _normalize_query_params(query: dict | None) -> dict:
        if not query:
            return {}
        normalized: dict[str, str | int | float | bool] = {}
        for key, value in query.items():
            if isinstance(value, list):
                normalized[key] = ",".join(str(item) for item in value)
            else:
                normalized[key] = value
        return normalized

    def _run_x_create_post_tool(self, params: dict) -> str:
        payload = params.get("payload")
        if not isinstance(payload, dict):
            return "ERROR: payload must be an object."
        user_token = self._resolve_x_oauth2_user_token(params)
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

    def _run_x_get_mentions_tool(self, params: dict) -> str:
        user_id = str(params.get("user_id", "")).strip()
        if not user_id:
            return "ERROR: user_id is required."
        token = self._resolve_x_token(params)
        if not token:
            return (
                "ERROR: Missing X bearer token for mentions. "
                "Set X_BEARER_TOKEN, pass bearer_token, or configure "
                "X_CLIENT_ID/X_CLIENT_SECRET for auto token generation."
            )
        headers = {"Authorization": f"Bearer {token}"}
        query = self._normalize_query_params(params.get("query"))
        url = f"https://api.x.com/2/users/{user_id}/mentions"

        try:
            response = req.get(url, headers=headers, params=query, timeout=20)
            return (
                f"GET /2/users/{user_id}/mentions (bearer) "
                f"-> {response.status_code}: {response.text[:1200]}"
            )
        except Exception as exc:
            return f"X API error (get mentions): {exc}"
