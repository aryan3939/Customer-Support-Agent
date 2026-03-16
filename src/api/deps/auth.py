"""
Authentication dependencies for FastAPI routes.

Decodes Supabase-issued JWTs and extracts user identity + role.
Used as FastAPI dependencies to protect routes:

    @router.get("/tickets")
    async def list_tickets(user: CurrentUser = Depends(get_current_user)):
        ...

Supabase has migrated to ECC P-256 (ES256) JWT signing. We use the
JWKS endpoint to fetch the public key for verification — no shared
secret needed.
"""

from dataclasses import dataclass
from typing import Annotated

import jwt
from jwt import PyJWKClient
from fastapi import Depends, Header, HTTPException, status

from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# JWKS Client — fetches Supabase's public signing keys
# =============================================================================

# PyJWKClient caches keys automatically, so this is cheap after first call.
# The JWKS URL is: https://<project>.supabase.co/auth/v1/.well-known/jwks.json
_jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
_jwks_client = PyJWKClient(_jwks_url, cache_keys=True)


# =============================================================================
# Current User — returned by the auth dependency
# =============================================================================

@dataclass
class CurrentUser:
    """Authenticated user extracted from a Supabase JWT."""
    id: str          # Supabase auth.users.id (UUID string)
    email: str
    role: str        # "customer" or "admin"


# =============================================================================
# Auth Dependencies
# =============================================================================

async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    """
    Decode and validate a Supabase JWT from the Authorization header.

    Uses JWKS (JSON Web Key Set) to fetch the public key from Supabase,
    supporting both ES256 (ECC P-256, current) and HS256 (legacy).

    Raises 401 if the token is missing, expired, or invalid.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    # Strip "Bearer " prefix
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty bearer token",
        )

    try:
        # Fetch the signing key that matches the token's "kid" header
        signing_key = _jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "EdDSA", "HS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError as e:
        logger.warning("jwt_decode_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    except Exception as e:
        logger.warning("jwt_jwks_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed",
        )

    # Extract user info from JWT claims
    user_id = payload.get("sub", "")
    email = payload.get("email", "")
    user_metadata = payload.get("user_metadata", {})
    role = user_metadata.get("role", "customer")  # default to customer

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID",
        )

    return CurrentUser(id=user_id, email=email, role=role)


async def require_admin(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """
    Dependency that enforces admin role.

    Usage:
        @router.get("/admin/conversations")
        async def admin_list(user: CurrentUser = Depends(require_admin)):
            ...
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
