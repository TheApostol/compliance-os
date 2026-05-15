"""
ComplianceOS — JWT Authentication
====================================
HS256 tokens signed with APP_SECRET_KEY.

JWT claims:
  sub         — user UUID
  tenant_id   — tenant slug (e.g. "polkorp")
  role        — admin | analyst | viewer
  exp         — expiry timestamp

Dev-mode backward compat: if JWT is absent but X-Tenant-Id header is present
and APP_ENV != production, requests are allowed through with role=analyst.
This lets existing dev/test scripts keep working without breaking auth.

Upgrade path: swap HS256 signing to JWKS (Auth0/Clerk) by replacing
`decode_token` without touching any downstream code.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8-hour sessions
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


# ── Password utilities ──────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── Token creation / decoding ───────────────────────────────────────

def create_access_token(
    user_id: str,
    tenant_id: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, get_settings().app_secret_key, algorithm=ALGORITHM)


def create_refresh_token(
    user_id: str,
    tenant_id: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(payload, get_settings().app_secret_key, algorithm=ALGORITHM)


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode and validate a refresh JWT. Raises HTTPException 401 if invalid or wrong type."""
    try:
        payload = jwt.decode(token, get_settings().app_secret_key, algorithms=[ALGORITHM])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired refresh token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not a refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate JWT. Raises HTTPException 401 on failure."""
    try:
        return jwt.decode(token, get_settings().app_secret_key, algorithms=[ALGORITHM])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── FastAPI dependency ──────────────────────────────────────────────

class CurrentUser:
    def __init__(self, user_id: str, tenant_id: str, role: str):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
) -> CurrentUser:
    """
    Resolve the current user from JWT (preferred) or X-Tenant-Id header (dev fallback).
    Raises 401 in production if no JWT is provided.
    """
    settings = get_settings()

    if token:
        claims = decode_token(token)
        return CurrentUser(
            user_id=claims["sub"],
            tenant_id=claims["tenant_id"],
            role=claims.get("role", "analyst"),
        )

    # Dev-mode fallback: allow X-Tenant-Id without JWT
    if not settings.is_production and x_tenant_id:
        return CurrentUser(
            user_id="dev-user",
            tenant_id=x_tenant_id,
            role="analyst",
        )

    # Default tenant in dev if nothing provided
    if not settings.is_production:
        return CurrentUser(
            user_id="dev-user",
            tenant_id=settings.default_tenant_id,
            role="analyst",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dependency: enforce admin role."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user
