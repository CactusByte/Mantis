"""Retry Anthropic Messages API calls when rate-limited (429).

The SDK retries 429s only a few times and ignores Retry-After when it is > 60s,
which is too aggressive for input-token-per-minute limits.
"""

from __future__ import annotations

import email.utils
import logging
import random
import time
from typing import Any, Callable, TypeVar

import anthropic

T = TypeVar("T")

# Do not sleep longer than this on a single 429 (safety against bogus headers).
_MAX_SINGLE_WAIT_S = 600
# Total attempts including the first try.
_DEFAULT_MAX_ATTEMPTS = 12


def _parse_retry_after_seconds(headers: Any) -> float | None:
    """Seconds to wait from Retry-After or Retry-After-Ms (same idea as Anthropic SDK)."""
    if headers is None:
        return None
    try:
        retry_ms = headers.get("retry-after-ms")
        if retry_ms is not None:
            return float(retry_ms) / 1000.0
    except (TypeError, ValueError):
        pass
    retry_raw = headers.get("retry-after")
    if retry_raw is None:
        return None
    try:
        return float(retry_raw)
    except (TypeError, ValueError):
        pass
    retry_date_tuple = email.utils.parsedate_tz(retry_raw)
    if retry_date_tuple is None:
        return None
    retry_ts = email.utils.mktime_tz(retry_date_tuple)
    return float(retry_ts - time.time())


def _backoff_seconds(attempt_index: int) -> float:
    """Exponential backoff when the API does not send Retry-After."""
    base = min(2.0 * (2**attempt_index), 90.0)
    return base * (0.75 + 0.25 * random.random())


def messages_create_with_rate_limit(
    call: Callable[[], T],
    *,
    log: logging.Logger,
    max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
) -> T:
    """
    Run ``call()`` (typically one Anthropic ``messages.create``), retrying on 429
    using Retry-After and exponential backoff. Re-raises the last RateLimitError if exhausted.
    """
    last_err: anthropic.RateLimitError | None = None
    for attempt in range(max_attempts):
        try:
            return call()
        except anthropic.RateLimitError as e:
            last_err = e
            if attempt == max_attempts - 1:
                raise
            wait = _parse_retry_after_seconds(e.response.headers)
            if wait is None or wait <= 0:
                wait = _backoff_seconds(attempt)
            else:
                wait = min(wait, _MAX_SINGLE_WAIT_S)
                wait += random.uniform(0, 0.5)
            log.warning(
                "Anthropic rate limited (429), retry %s/%s in %.1fs",
                attempt + 1,
                max_attempts,
                wait,
            )
            time.sleep(wait)
    assert last_err is not None
    raise last_err
