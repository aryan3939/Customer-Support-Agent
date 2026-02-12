"""
API Key Authentication Middleware.

WHY THIS EXISTS:
----------------
In production, you don't want anyone hitting your API. This middleware
validates API keys in request headers before allowing access.

HOW IT WORKS:
    Client sends: Authorization: Bearer sk-abc123
    Middleware checks: is this key valid?
    If yes → request proceeds
    If no  → 401 Unauthorized
"""

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Define where to look for the API key in the request
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(api_key_header)) -> str:
    """
    FastAPI dependency that validates the API key.
    
    Usage in routes:
        @router.get("/protected")
        async def protected_route(key: str = Depends(verify_api_key)):
            return {"message": "Authenticated!"}
    
    For development: skip authentication if DEBUG=True
    """
    # In development mode, allow requests without API key
    if settings.DEBUG:
        return "dev-mode"
    
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include 'X-API-Key' header.",
        )
    
    # In production, validate against stored keys
    # For now, accept any non-empty key in debug mode
    if api_key == settings.JWT_SECRET:
        return api_key
    
    logger.warning("invalid_api_key_attempt", key_prefix=api_key[:8] + "...")
    raise HTTPException(status_code=401, detail="Invalid API key.")
