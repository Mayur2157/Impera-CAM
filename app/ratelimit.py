"""Fixed-window request limits, counted in Redis so every API process shares them."""
from __future__ import annotations

import logging
import time

import redis
from fastapi import HTTPException, Request

from .worker import redis_client

log = logging.getLogger("bsx.ratelimit")


def client_ip(request: Request) -> str:
    # behind a reverse proxy uvicorn --proxy-headers puts the real client here
    return request.client.host if request.client else "unknown"


def hit(bucket: str, who: str, cap: int, window_seconds: int,
        message: str = "too many attempts — wait a minute and try again") -> None:
    """Count one request by ``who``; raise 429 once the window's cap is passed."""
    window = int(time.time() // window_seconds)
    key = f"bsx:rl:{bucket}:{who}:{window}"
    try:
        r = redis_client()
        hits = r.incr(key)
        if hits == 1:
            r.expire(key, window_seconds)
    except redis.RedisError:
        # fail open: a Redis outage must not lock every user out of login
        log.warning("rate limit %s skipped: redis unavailable", bucket)
        return
    if hits > cap:
        raise HTTPException(429, message, headers={"Retry-After": str(window_seconds)})


def limit(bucket: str, max_hits, window_seconds: int):
    """FastAPI dependency. ``max_hits`` may be a callable so tests can tune it."""
    def dependency(request: Request) -> None:
        cap = max_hits() if callable(max_hits) else max_hits
        hit(bucket, client_ip(request), cap, window_seconds)
    return dependency
