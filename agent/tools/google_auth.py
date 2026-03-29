from __future__ import annotations

import requests as req

from ..config import Settings
from .base import ToolContext


def google_access_token(settings: Settings, ctx: ToolContext) -> str | None:
    if ctx.google_token_ttl_ok():
        return ctx.google_access_token

    cid = settings.google_client_id
    secret = settings.google_client_secret
    refresh = settings.google_refresh_token
    if not cid or not secret or not refresh:
        return None

    try:
        response = req.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": cid,
                "client_secret": secret,
                "refresh_token": refresh,
                "grant_type": "refresh_token",
            },
            timeout=20,
        )
        if not response.ok:
            return None
        data = response.json()
        token = data.get("access_token")
        expires_in = int(data.get("expires_in", 3600))
        if isinstance(token, str) and token:
            ctx.set_google_token(token, expires_in)
            return token
    except Exception:
        return None
    return None
