"""In-memory per-IP rate limiter."""

from __future__ import annotations

import os
import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, status

_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() not in ("0", "false", "no")


class RateLimiter:
    def __init__(self, *, max_calls: int, period_seconds: float, name: str = "limit"):
        self.max_calls = max_calls
        self.period = period_seconds
        self.name = name
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def hit(self, key: str) -> None:
        if not _ENABLED:
            return
        now = time.monotonic()
        with self._lock:
            window = [t for t in self._hits[key] if now - t < self.period]
            if len(window) >= self.max_calls:
                self._hits[key] = window
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded ({self.name}). Try again shortly.",
                    headers={"Retry-After": str(int(self.period))},
                )
            window.append(now)
            self._hits[key] = window


generate_limiter = RateLimiter(max_calls=30, period_seconds=60, name="generate")
write_limiter = RateLimiter(max_calls=60, period_seconds=60, name="write")


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"
