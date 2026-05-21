"""
T5 — JWKS validator and auth mode routing tests.

Tests:
  1. test_jwks_validator_caches_keys         — after first decode, _fetch_keys not called again within 1 hour
  2. test_jwks_validator_refreshes_on_unknown_kid — unknown kid triggers one refresh attempt
  3. test_jwks_validator_raises_401_on_invalid_token — bad token → HTTPException 401
  4. test_get_current_user_auth0_mode        — auth_mode="auth0" → CurrentUser from JWKS claims
  5. test_get_current_user_local_mode_unchanged — auth_mode="local" → HS256 decode path used
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.auth import CurrentUser, JWKSValidator, _get_jwks_validator, create_access_token


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_jwks_response(kid: str = "test-kid-1") -> dict:
    """Minimal JWKS structure; actual key bytes don't matter for cache/routing tests."""
    return {
        "keys": [
            {
                "kid": kid,
                "kty": "RSA",
                "use": "sig",
                "n": "fake-n-value",
                "e": "AQAB",
            }
        ]
    }


def _make_mock_httpx_response(json_data: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


# ── 1. Key caching ────────────────────────────────────────────────────────────


class TestJWKSValidatorCaching:
    @pytest.mark.asyncio
    async def test_jwks_validator_caches_keys(self):
        """After the first successful fetch, _fetch_keys must not hit the network again
        for at least 1 hour."""
        validator = JWKSValidator(
            jwks_url="https://example.auth0.com/.well-known/jwks.json",
            audience="https://api.complianceos.io",
            issuer="https://example.auth0.com/",
        )

        mock_response = _make_mock_httpx_response(_make_jwks_response("kid-abc"))

        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(return_value=MockClient.return_value)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value.get = AsyncMock(return_value=mock_response)

            # First fetch — populates the cache
            await validator._fetch_keys()
            assert MockClient.return_value.get.call_count == 1

            # Simulate time well within the 1-hour window
            validator._fetched_at = time.time() - 100  # 100 seconds ago

            # Second call — should NOT trigger a new HTTP request
            await validator._fetch_keys()
            assert MockClient.return_value.get.call_count == 1  # still 1

    @pytest.mark.asyncio
    async def test_jwks_validator_refetches_after_ttl(self):
        """After 1 hour the cache must be refreshed."""
        validator = JWKSValidator(jwks_url="https://example.auth0.com/.well-known/jwks.json")

        mock_response = _make_mock_httpx_response(_make_jwks_response("kid-xyz"))

        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(return_value=MockClient.return_value)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value.get = AsyncMock(return_value=mock_response)

            # Simulate stale cache (fetched > 1 hour ago)
            validator._keys = {"kid-xyz": {"kid": "kid-xyz"}}
            validator._fetched_at = time.time() - 3601  # just over 1 hour

            await validator._fetch_keys()
            assert MockClient.return_value.get.call_count == 1


# ── 2. Unknown kid triggers refresh ──────────────────────────────────────────


class TestJWKSValidatorUnknownKid:
    @pytest.mark.asyncio
    async def test_jwks_validator_refreshes_on_unknown_kid(self):
        """If the token's kid is not in the cached keys, the validator must refresh
        once before giving up with a 401."""
        validator = JWKSValidator(jwks_url="https://example.auth0.com/.well-known/jwks.json")

        # Pre-load cache with a *different* kid so first lookup misses
        validator._keys = {"old-kid": {"kid": "old-kid"}}
        validator._fetched_at = time.time()  # cache looks fresh

        # After refresh, JWKS still doesn't have the requested kid
        fresh_response = _make_mock_httpx_response(_make_jwks_response("still-different-kid"))

        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(return_value=MockClient.return_value)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value.get = AsyncMock(return_value=fresh_response)

            with patch("jose.jwt.get_unverified_header") as mock_header:
                mock_header.return_value = {"kid": "new-kid", "alg": "RS256"}

                with pytest.raises(HTTPException) as exc_info:
                    await validator.decode("header.payload.signature")

                assert exc_info.value.status_code == 401
                assert "Unknown signing key" in exc_info.value.detail

                # The network was hit exactly once (the refresh attempt)
                assert MockClient.return_value.get.call_count == 1


# ── 3. Invalid token → 401 ────────────────────────────────────────────────────


class TestJWKSValidatorInvalidToken:
    @pytest.mark.asyncio
    async def test_jwks_validator_raises_401_on_invalid_token(self):
        """A completely malformed token must raise HTTPException 401."""
        validator = JWKSValidator(jwks_url="https://example.auth0.com/.well-known/jwks.json")

        # No network call needed — JWTError is raised before key lookup
        with pytest.raises(HTTPException) as exc_info:
            await validator.decode("this.is.not.a.valid.jwt.at.all")

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_jwks_validator_raises_401_on_decode_failure(self):
        """A token with a valid header but bad signature must raise HTTPException 401."""
        from jose import JWTError

        validator = JWKSValidator(
            jwks_url="https://example.auth0.com/.well-known/jwks.json",
            audience="https://api.complianceos.io",
            issuer="https://example.auth0.com/",
        )
        # Pre-seed the cache so key lookup succeeds
        validator._keys = {"kid-1": {"kid": "kid-1", "kty": "RSA"}}
        validator._fetched_at = time.time()

        with patch("jose.jwt.get_unverified_header") as mock_header:
            mock_header.return_value = {"kid": "kid-1", "alg": "RS256"}

            with patch("jose.jwt.decode") as mock_decode:
                mock_decode.side_effect = JWTError("signature verification failed")

                with pytest.raises(HTTPException) as exc_info:
                    await validator.decode("header.payload.badsig")

                assert exc_info.value.status_code == 401
                assert "Token validation failed" in exc_info.value.detail


# ── 4. get_current_user — Auth0 mode ─────────────────────────────────────────


class TestGetCurrentUserAuth0Mode:
    @pytest.mark.asyncio
    async def test_get_current_user_auth0_mode(self):
        """When auth_mode='auth0', get_current_user must route through the JWKS
        validator and correctly map the custom tenant_id claim."""
        from app.core import auth as auth_module
        from app.core.config import Settings
        from starlette.requests import Request as StarletteRequest

        # Build fake Auth0 claims with the custom namespace claim
        fake_claims = {
            "sub": "auth0|user-abc-123",
            "https://complianceos.io/tenant_id": "acme-corp",
            "https://complianceos.io/role": "admin",
            "iss": "https://my-tenant.auth0.com/",
            "aud": "https://api.complianceos.io",
        }

        # Mock validator that returns the fake claims
        mock_validator = AsyncMock(spec=JWKSValidator)
        mock_validator.decode = AsyncMock(return_value=fake_claims)

        fake_settings = Settings(
            app_secret_key="test-secret-key-for-pytest-32bytes!!",
            app_env="development",
            auth_mode="auth0",
            auth0_domain="my-tenant.auth0.com",
            auth0_audience="https://api.complianceos.io",
        )

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [(b"authorization", b"Bearer fake.rs256.token")],
            "query_string": b"",
        }
        request = StarletteRequest(scope)

        with patch.object(auth_module, "get_settings", return_value=fake_settings):
            with patch.object(auth_module, "_get_jwks_validator", return_value=mock_validator):
                user = await auth_module.get_current_user(
                    request=request,
                    authorization="Bearer fake.rs256.token",
                )

        assert user.user_id == "auth0|user-abc-123"
        assert user.tenant_id == "acme-corp"
        assert user.role == "admin"
        assert user.is_admin is True

    @pytest.mark.asyncio
    async def test_get_current_user_auth0_org_id_fallback(self):
        """When tenant_id custom claim is absent, fall back to org_id."""
        from app.core import auth as auth_module
        from app.core.config import Settings
        from starlette.requests import Request as StarletteRequest

        fake_claims = {
            "sub": "auth0|user-xyz",
            "org_id": "org_polkorp",
            "role": "analyst",
        }

        mock_validator = AsyncMock(spec=JWKSValidator)
        mock_validator.decode = AsyncMock(return_value=fake_claims)

        fake_settings = Settings(
            app_secret_key="test-secret-key-for-pytest-32bytes!!",
            app_env="development",
            auth_mode="auth0",
            auth0_domain="my-tenant.auth0.com",
        )

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [(b"authorization", b"Bearer fake.token")],
            "query_string": b"",
        }
        request = StarletteRequest(scope)

        with patch.object(auth_module, "get_settings", return_value=fake_settings):
            with patch.object(auth_module, "_get_jwks_validator", return_value=mock_validator):
                user = await auth_module.get_current_user(
                    request=request,
                    authorization="Bearer fake.token",
                )

        assert user.tenant_id == "org_polkorp"
        assert user.role == "analyst"


# ── 5. get_current_user — local mode unchanged ────────────────────────────────


class TestGetCurrentUserLocalMode:
    @pytest.mark.asyncio
    async def test_get_current_user_local_mode_unchanged(self):
        """When auth_mode='local', the HS256 decode path must be used exclusively —
        JWKSValidator must never be instantiated or called."""
        from app.core import auth as auth_module
        from app.core.config import Settings
        from starlette.requests import Request as StarletteRequest

        # Create a real HS256 token
        token = create_access_token(
            user_id="local-user-99",
            tenant_id="polkorp",
            role="analyst",
        )

        fake_settings = Settings(
            app_secret_key="test-secret-key-for-pytest-32bytes!!",
            app_env="development",
            auth_mode="local",
        )

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [(b"authorization", f"Bearer {token}".encode())],
            "query_string": b"",
        }
        request = StarletteRequest(scope)

        mock_validator = AsyncMock(spec=JWKSValidator)

        with patch.object(auth_module, "get_settings", return_value=fake_settings):
            with patch.object(auth_module, "_get_jwks_validator", return_value=mock_validator):
                user = await auth_module.get_current_user(
                    request=request,
                    authorization=f"Bearer {token}",
                )

        # JWKS validator decode must NOT have been called
        mock_validator.decode.assert_not_called()

        assert user.user_id == "local-user-99"
        assert user.tenant_id == "polkorp"
        assert user.role == "analyst"

    @pytest.mark.asyncio
    async def test_get_current_user_local_dev_fallback(self):
        """In local mode without a token, dev fallback uses X-Tenant-Id header."""
        from app.core import auth as auth_module
        from app.core.config import Settings
        from starlette.requests import Request as StarletteRequest

        fake_settings = Settings(
            app_secret_key="test-secret-key-for-pytest-32bytes!!",
            app_env="development",
            auth_mode="local",
            default_tenant_id="polkorp",
        )

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [(b"x-tenant-id", b"demo-tenant")],
            "query_string": b"",
        }
        request = StarletteRequest(scope)

        with patch.object(auth_module, "get_settings", return_value=fake_settings):
            user = await auth_module.get_current_user(
                request=request,
                authorization=None,
            )

        assert user.tenant_id == "demo-tenant"
        assert user.user_id == "dev"
        assert user.role == "admin"

    @pytest.mark.asyncio
    async def test_get_current_user_production_no_token_raises_401(self):
        """In production with no token, must raise 401 — no dev fallback."""
        from app.core import auth as auth_module
        from app.core.config import Settings
        from starlette.requests import Request as StarletteRequest

        fake_settings = Settings(
            app_secret_key="test-secret-key-for-pytest-32bytes!!",
            app_env="production",
            auth_mode="local",
        )

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [],
            "query_string": b"",
        }
        request = StarletteRequest(scope)

        with patch.object(auth_module, "get_settings", return_value=fake_settings):
            with pytest.raises(HTTPException) as exc_info:
                await auth_module.get_current_user(
                    request=request,
                    authorization=None,
                )

        assert exc_info.value.status_code == 401
