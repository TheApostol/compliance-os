"""
T2 — Authentication unit tests.

Tests:
  - hash_password / verify_password round-trip
  - create_access_token + decode_token round-trip
  - decode_token with tampered/invalid token → HTTPException 401
  - CurrentUser.is_admin: True only for role="admin"
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.core.auth import (
    CurrentUser,
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


# ── Password utilities ────────────────────────────────────────────────────────


class TestPasswordHashing:
    def test_hash_is_not_plain_text(self):
        plain = "SuperSecret123!"
        hashed = hash_password(plain)
        assert hashed != plain

    def test_round_trip_correct_password(self):
        plain = "SuperSecret123!"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_wrong_password_fails(self):
        plain = "SuperSecret123!"
        hashed = hash_password(plain)
        assert verify_password("WrongPassword!", hashed) is False

    def test_empty_password_fails_verify(self):
        plain = "ActualPassword99"
        hashed = hash_password(plain)
        assert verify_password("", hashed) is False

    def test_different_hashes_for_same_password(self):
        """bcrypt salts should produce different hashes each time."""
        plain = "SamePassword99"
        h1 = hash_password(plain)
        h2 = hash_password(plain)
        assert h1 != h2
        # But both should verify correctly
        assert verify_password(plain, h1) is True
        assert verify_password(plain, h2) is True


# ── Token create / decode ─────────────────────────────────────────────────────


class TestJWT:
    def test_round_trip_returns_correct_sub(self):
        token = create_access_token(
            user_id="user-abc-123",
            tenant_id="polkorp",
            role="analyst",
        )
        claims = decode_token(token)
        assert claims["sub"] == "user-abc-123"

    def test_round_trip_returns_correct_tenant_id(self):
        token = create_access_token(
            user_id="u1",
            tenant_id="acme-corp",
            role="viewer",
        )
        claims = decode_token(token)
        assert claims["tenant_id"] == "acme-corp"

    def test_round_trip_returns_correct_role(self):
        for role in ("admin", "analyst", "viewer"):
            token = create_access_token(user_id="u1", tenant_id="t1", role=role)
            claims = decode_token(token)
            assert claims["role"] == role

    def test_token_is_string(self):
        token = create_access_token(user_id="u1", tenant_id="t1", role="analyst")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_custom_expiry_respected(self):
        """A token with a very short expiry (but not yet expired) should decode."""
        token = create_access_token(
            user_id="u1",
            tenant_id="t1",
            role="analyst",
            expires_delta=timedelta(hours=1),
        )
        claims = decode_token(token)
        assert claims["sub"] == "u1"

    def test_tampered_token_raises_401(self):
        token = create_access_token(user_id="u1", tenant_id="t1", role="analyst")
        # Tamper: flip some characters in the signature part
        parts = token.split(".")
        assert len(parts) == 3, "JWT should have three dot-separated parts"
        parts[2] = parts[2][::-1]  # reverse the signature
        bad_token = ".".join(parts)
        with pytest.raises(HTTPException) as exc_info:
            decode_token(bad_token)
        assert exc_info.value.status_code == 401

    def test_completely_invalid_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_token("this.is.not.a.valid.jwt")
        assert exc_info.value.status_code == 401

    def test_empty_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_token("")
        assert exc_info.value.status_code == 401

    def test_wrong_secret_raises_401(self, monkeypatch):
        """Token signed with a different secret key must fail decode."""
        # Create a token with the real key
        token = create_access_token(user_id="u1", tenant_id="t1", role="analyst")

        # Monkey-patch get_settings to return a different secret
        from app.core import auth as auth_module
        from app.core.config import Settings

        fake_settings = Settings(
            app_secret_key="completely-different-secret-key-xyz!",
            app_env="development",
        )
        monkeypatch.setattr(auth_module, "get_settings", lambda: fake_settings)

        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == 401


# ── CurrentUser ───────────────────────────────────────────────────────────────


class TestCurrentUser:
    def test_is_admin_true_for_admin_role(self):
        user = CurrentUser(user_id="u1", tenant_id="t1", role="admin")
        assert user.is_admin is True

    def test_is_admin_false_for_analyst_role(self):
        user = CurrentUser(user_id="u1", tenant_id="t1", role="analyst")
        assert user.is_admin is False

    def test_is_admin_false_for_viewer_role(self):
        user = CurrentUser(user_id="u1", tenant_id="t1", role="viewer")
        assert user.is_admin is False

    def test_is_admin_false_for_empty_role(self):
        user = CurrentUser(user_id="u1", tenant_id="t1", role="")
        assert user.is_admin is False

    def test_attributes_stored_correctly(self):
        user = CurrentUser(user_id="abc", tenant_id="polkorp", role="analyst")
        assert user.user_id == "abc"
        assert user.tenant_id == "polkorp"
        assert user.role == "analyst"
