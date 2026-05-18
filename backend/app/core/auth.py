"""
ComplianceOS — JWT Authentication
====================================
HS256 tokens signed with APP_SECRET_KEY (local mode).
RS256 tokens validated against remote JWKS (Auth0 / Clerk modes).

JWT claims (local HS256):
  sub         — user UUID
  tenant_id   — tenant slug (e.g. "polkorp")
  role        — admin | analyst | viewer
  exp         — expiry timestamp

JWT claims (Auth0):
  sub                                  — "auth0|<user_id>"
  https://complianceos.io/tenant_id    — tenant slug (custom claim)
  https://complianceos.io/role         — role (custom claim)

JWT claims (Clerk):
  sub     — "user_<id>"
  org_id  — mapped to tenant_id
  role    — mapped to role

Dev-mode backward compat: if JWT is absent but X-Tenant-Id header is present
and APP_ENV != production, requests are allowed through with role=analyst.
This lets existing dev/test scripts keep working without breaking auth.

Auth modes:
  local  — HS256 signed with APP_SECRET_KEY (default)
  auth0  — RS256 validated against Auth0 JWKS endpoint
  clerk  — RS256 validated against Clerk JWKS endpoint
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import Depends, Header, HTTPException, Request, status
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


# ── JWKS Validator (Auth0 / Clerk) ──────────────────────────────────

class JWKSValidator:
    """Validates RS256 JWTs against a remote JWKS endpoint. Caches keys for 1 hour."""

    def __init__(self, jwks_url: str, audience: str = "", issuer: str = ""):
        self.jwks_url = jwks_url
        self.audience = audience
        self.issuer = issuer
        self._keys: dict[str, Any] = {}
        self._fetched_at: float = 0.0

    async def _fetch_keys(self) -> None:
        if time.time() - self._fetched_at < 3600 and self._keys:
            return
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(self.jwks_url)
            resp.raise_for_status()
            jwks = resp.json()
        self._keys = {k["kid"]: k for k in jwks.get("keys", [])}
        self._fetched_at = time.time()

    async def decode(self, token: str) -> dict:
        """Decode and validate an RS256 JWT. Returns claims dict or raises HTTPException 401."""
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token header")

        await self._fetch_keys()
        key_data = self._keys.get(kid)
        if not key_data:
            # Refresh once and retry
            self._fetched_at = 0.0
            await self._fetch_keys()
            key_data = self._keys.get(kid)
        if not key_data:
            raise HTTPException(status_code=401, detail="Unknown signing key")

        try:
            options = {"verify_aud": bool(self.audience), "verify_iss": bool(self.issuer)}
            claims = jwt.decode(
                token,
                key_data,
                algorithms=["RS256"],
                audience=self.audience or None,
                issuer=self.issuer or None,
                options=options,
            )
            return claims
        except JWTError as e:
            raise HTTPException(status_code=401, detail=f"Token validation failed: {e}")


# ── JWKS singleton ──────────────────────────────────────────────────

_jwks_validator: JWKSValidator | None = None


def _get_jwks_validator() -> JWKSValidator | None:
    global _jwks_validator
    settings = get_settings()
    if settings.auth_mode == "auth0" and settings.auth0_domain:
        if _jwks_validator is None:
            _jwks_validator = JWKSValidator(
                jwks_url=f"https://{settings.auth0_domain}/.well-known/jwks.json",
                audience=settings.auth0_audience,
                issuer=f"https://{settings.auth0_domain}/",
            )
        return _jwks_validator
    if settings.auth_mode == "clerk" and settings.clerk_jwks_url:
        if _jwks_validator is None:
            _jwks_validator = JWKSValidator(jwks_url=settings.clerk_jwks_url)
        return _jwks_validator
    return None


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


async def get_current_user_or_key(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> CurrentUser:
    """
    Accept either a Bearer JWT (Authorization header) or an X-API-Key header.

    API key auth is tried first. If the header is present but invalid, a 401 is
    raised immediately — no fallback to JWT. If no X-API-Key is present, the
    normal JWT / dev-fallback path is used.

    This prevents API keys from being used to create more API keys
    (key-management endpoints require plain JWT auth via get_current_user).
    """
    if x_api_key:
        from app.services.api_key_service import validate_key

        key_data = await validate_key(x_api_key)
        if key_data:
            return CurrentUser(
                user_id=f"apikey:{key_data['key_id']}",
                tenant_id=key_data["tenant_id"],
                role="analyst",  # API keys always get analyst role
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    # Fall through to normal JWT / dev-fallback auth
    return await get_current_user(token=token, x_tenant_id=x_tenant_id)
