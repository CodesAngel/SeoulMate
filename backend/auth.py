"""Supabase access-token verification for protected FastAPI routes."""

from functools import lru_cache
from typing import Any
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from pydantic import BaseModel

from database.settings import get_database_settings


class AuthenticatedUser(BaseModel):
    id: UUID
    email: str | None = None
    role: str


bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def get_jwks_client() -> PyJWKClient:
    settings = get_database_settings()
    jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    return PyJWKClient(jwks_url, cache_keys=True)


def _unauthorized(detail: str = "Invalid or expired access token") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    """Validate a Supabase JWT and return the authenticated identity."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Authentication required")

    settings = get_database_settings()
    issuer = f"{settings.supabase_url.rstrip('/')}/auth/v1"

    try:
        signing_key = get_jwks_client().get_signing_key_from_jwt(credentials.credentials)
        claims: dict[str, Any] = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
            issuer=issuer,
        )
        subject = UUID(claims["sub"])
    except (KeyError, TypeError, ValueError, jwt.PyJWTError) as exc:
        raise _unauthorized() from exc

    role = claims.get("role")
    if role != "authenticated":
        raise _unauthorized()

    email = claims.get("email")
    return AuthenticatedUser(
        id=subject,
        email=email if isinstance(email, str) else None,
        role=role,
    )


def optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser | None:
    """Optionally validate a Supabase JWT without failing anonymous visitors."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None

    settings = get_database_settings()
    issuer = f"{settings.supabase_url.rstrip('/')}/auth/v1"

    try:
        signing_key = get_jwks_client().get_signing_key_from_jwt(credentials.credentials)
        claims: dict[str, Any] = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
            issuer=issuer,
        )
        subject = UUID(claims["sub"])
        role = claims.get("role")
        if role != "authenticated":
            return None
        email = claims.get("email")
        return AuthenticatedUser(
            id=subject,
            email=email if isinstance(email, str) else None,
            role=role,
        )
    except Exception:
        return None

