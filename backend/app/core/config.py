"""
ComplianceOS — Core Configuration

Centralizes all settings with strict validation.
Compatible with Pydantic v2 + pydantic-settings.

CORS parsing accepts:
  - JSON array:  CORS_ORIGINS=["http://localhost:3000"]
  - CSV string:  CORS_ORIGINS=http://localhost:3000,http://localhost:3001
  - Python list: cors_origins=["..."]
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Annotated

from pydantic import Field, field_validator
from pydantic.functional_validators import BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_cors(v: Any) -> list[str]:
    if not v:
        return ["http://localhost:3000"]
    if isinstance(v, list):
        return [str(x).strip() for x in v if x]
    if isinstance(v, str):
        v = v.strip()
        if not v:
            return ["http://localhost:3000"]
        if v.startswith("["):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed]
            except json.JSONDecodeError:
                pass
        return [o.strip() for o in v.split(",") if o.strip()]
    return ["http://localhost:3000"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────
    app_name: str = "ComplianceOS"
    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = Field(default="dev-secret-change-me", min_length=16)
    log_level: str = "INFO"

    # ── API ────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # ── Database ───────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://complianceos:complianceos@db:5432/complianceos"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: Any) -> str:
        """Railway provides postgres:// — normalize to postgresql+asyncpg://."""
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://") and "+asyncpg" not in v:
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    postgres_user: str = "complianceos"
    postgres_password: str = "complianceos"
    postgres_db: str = "complianceos"
    postgres_host: str = "db"
    postgres_port: int = 5432

    # ── Vector DB ──────────────────────────────────────────
    qdrant_url: str = "http://qdrant:6333"
    qdrant_api_key: str = ""

    # ── Cache / Queue ──────────────────────────────────────
    redis_url: str = "redis://redis:6379/0"

    # ── AI Providers ───────────────────────────────────────
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_rate_limit_rpm: int = 40

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openrouter_api_key: str = ""

    # ── Audit ──────────────────────────────────────────────
    audit_log_retention_days: int = 2555
    audit_hash_chain_enabled: bool = True

    # ── Multi-tenancy ──────────────────────────────────────
    default_tenant_id: str = "polkorp"
    default_tenant_name: str = "Polkorp Global Ventures"

    # ── Auth (external — optional) ─────────────────────────
    auth_mode: str = "local"          # "local" | "auth0" | "clerk"
    auth0_domain: str = ""            # e.g. "your-tenant.auth0.com"
    auth0_audience: str = ""          # e.g. "https://api.complianceos.io"
    clerk_jwks_url: str = ""          # e.g. "https://clerk.your-app.com/.well-known/jwks.json"

    # ── Crawler ────────────────────────────────────────────
    crawler_enabled: bool = True
    crawler_bcra_url: str = "https://www.bcra.gob.ar/SistemasFinancieros/sf_comunicaciones.asp"
    crawler_uif_url: str = "https://www.uif.gob.ar/uif/index.php/es/normativa"

    # ── Convenience flags ──────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def has_nvidia(self) -> bool:
        return bool(self.nvidia_api_key and self.nvidia_api_key.startswith("nvapi-"))


@lru_cache
def get_settings() -> Settings:
    """Cached singleton. Use this everywhere."""
    return Settings()


settings = get_settings()


if __name__ == "__main__":
    s = get_settings()
    print(f"✓ App: {s.app_name} ({s.app_env})")
    print(f"✓ CORS origins ({len(s.cors_origins_list)}):")
    for o in s.cors_origins_list:
        print(f"  - {o}")
    print(f"✓ NVIDIA configured: {s.has_nvidia}")
