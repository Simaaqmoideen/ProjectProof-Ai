"""In-memory rate limiter with sliding window.
See docs/04-api-specification.md and FR-CRT-6.
"""

import time
from collections import defaultdict
from threading import Lock

from fastapi import Request

from app.core.errors import RateLimitedError

_request_timestamps: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


TRUSTED_PROXIES = {"127.0.0.1", "::1", "localhost", "testclient"}


def parse_rate_limit(rate_str: str) -> tuple[int, float]:
    """Parse string like '30/minute' or '5/minute' into (max_requests, window_seconds)."""
    parts = rate_str.split("/")
    count = int(parts[0])
    period = parts[1].lower() if len(parts) > 1 else "minute"
    if period in ("minute", "m"):
        window = 60.0
    elif period in ("hour", "h"):
        window = 3600.0
    elif period in ("second", "s"):
        window = 1.0
    elif period in ("day", "d"):
        window = 86400.0
    else:
        window = 60.0
    return count, window


def check_rate_limit(
    key: str,
    max_requests: int = 30,
    window_seconds: float = 60.0,
) -> None:
    """Check if the given key exceeded rate limit. Raises RateLimitedError if exceeded."""
    now = time.time()
    cutoff = now - window_seconds
    with _lock:
        timestamps = _request_timestamps.get(key, [])
        # Keep only timestamps in current window
        valid = [ts for ts in timestamps if ts > cutoff]
        if len(valid) >= max_requests:
            _request_timestamps[key] = valid
            raise RateLimitedError("Rate limit exceeded. Please try again later.")
        valid.append(now)
        _request_timestamps[key] = valid

        # Periodic cleanup of empty or fully expired keys
        if len(_request_timestamps) > 100:
            stale = [k for k, v in _request_timestamps.items() if not v or v[-1] <= cutoff]
            for k in stale:
                _request_timestamps.pop(k, None)


def get_client_ip(request: Request) -> str:
    """Extract client IP from X-Forwarded-For if behind trusted proxy, else direct client."""
    client_host = request.client.host if request.client else "127.0.0.1"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded and client_host in TRUSTED_PROXIES:
        return forwarded.split(",")[0].strip()
    return client_host


def reset_rate_limits() -> None:
    """Clear all rate limit state (useful in tests)."""
    with _lock:
        _request_timestamps.clear()
