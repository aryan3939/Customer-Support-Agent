"""
Rate Limiting Middleware.

WHY THIS EXISTS:
----------------
LLM API calls are expensive and slow. Without rate limiting:
- A single user could spam 1000 tickets/second
- Exhaust your Google AI API quota in minutes
- Crash the server with concurrent LLM calls

This simple in-memory rate limiter tracks requests per IP.
Production would use Redis for distributed rate limiting.
"""

import time
from collections import defaultdict

from fastapi import HTTPException, Request

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Track request timestamps per IP
_request_log: dict[str, list[float]] = defaultdict(list)

# Config
MAX_REQUESTS_PER_MINUTE = 30
WINDOW_SECONDS = 60


async def rate_limit_check(request: Request) -> None:
    """
    FastAPI dependency that enforces rate limits per client IP.
    
    Usage:
        @router.post("/tickets", dependencies=[Depends(rate_limit_check)])
        async def create_ticket(...):
            ...
    """
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    
    # Clean old entries outside the window
    _request_log[client_ip] = [
        ts for ts in _request_log[client_ip]
        if now - ts < WINDOW_SECONDS
    ]
    
    if len(_request_log[client_ip]) >= MAX_REQUESTS_PER_MINUTE:
        logger.warning("rate_limit_exceeded", client_ip=client_ip)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {MAX_REQUESTS_PER_MINUTE} requests per minute.",
        )
    
    _request_log[client_ip].append(now)
