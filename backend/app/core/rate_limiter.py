"""Redis-based sliding window rate limiter middleware.

Uses a sorted set per key (IP + route group) with timestamps as scores.
On each request, removes expired entries, counts remaining, and decides
whether to allow or reject (429).

Complements the existing daily quota system in quota_service.py:
- quota_service: daily question limits per user/tier (business logic)
- rate_limiter: per-minute burst protection per IP (abuse prevention)
"""

import logging
import time

from fastapi import Request, Response
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from app.config import get_settings

logger = logging.getLogger(__name__)

# Route group → config key mapping.
# Matched by path prefix; first match wins. Unmatched routes use global limit.
ROUTE_LIMITS = [
    ("/api/v1/scan/solve", "rate_limit_solve_rpm"),
    ("/api/v1/scan/extract-text", "rate_limit_solve_rpm"),
    ("/api/v1/auth/", "rate_limit_auth_rpm"),
    ("/api/v1/scan/", "rate_limit_followup_rpm"),  # followup, stream, etc.
]


def _get_limit_for_path(path: str) -> tuple[str, int]:
    """Return (group_name, max_rpm) for a given request path."""
    settings = get_settings()
    for prefix, config_key in ROUTE_LIMITS:
        if path.startswith(prefix):
            return prefix, getattr(settings, config_key)
    return "global", settings.rate_limit_global_rpm


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For behind a proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter backed by Redis sorted sets."""

    def __init__(self, app, redis: Redis):
        super().__init__(app)
        self.redis = redis

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        settings = get_settings()

        if not settings.rate_limit_enabled:
            return await call_next(request)

        # Skip health checks and docs
        path = request.url.path
        if path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        # Skip non-API routes
        if not path.startswith("/api/"):
            return await call_next(request)

        client_ip = _get_client_ip(request)
        group, max_rpm = _get_limit_for_path(path)
        key = f"rl:{client_ip}:{group}"
        window = 60  # 1 minute

        try:
            allowed, remaining, retry_after = await self._check_rate(
                key, max_rpm, window
            )
        except Exception:
            # Redis down — fail open, don't block requests
            logger.warning("Rate limiter Redis error, allowing request")
            return await call_next(request)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_rpm),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_rpm)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    async def _check_rate(
        self, key: str, max_requests: int, window: int
    ) -> tuple[bool, int, int]:
        """Check and record a request. Returns (allowed, remaining, retry_after)."""
        now = time.time()
        window_start = now - window

        pipe = self.redis.pipeline()
        # Remove entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)
        # Count current entries
        pipe.zcard(key)
        # Add this request
        pipe.zadd(key, {str(now): now})
        # Set TTL so keys auto-expire
        pipe.expire(key, window + 1)
        results = await pipe.execute()

        current_count = results[1]  # zcard result (before adding this one)

        if current_count >= max_requests:
            # Over limit — find when the oldest entry expires
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                retry_after = int(oldest[0][1] + window - now) + 1
            else:
                retry_after = window
            # Remove the entry we just added since the request is denied
            await self.redis.zrem(key, str(now))
            return False, 0, retry_after

        remaining = max_requests - current_count - 1
        return True, remaining, 0
