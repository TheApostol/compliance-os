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
from typing import Any

from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    cors_origins: list[str] = ["http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Accept JSON array, CSV string, or list. Robust to common .env mistakes."""
        if v is None or v == "":
            return ["http://localhost:3000"]
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(x).strip() for x in parsed]
                except json.JSONDecodeError:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return list(v)

    # ── Database ───────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://complianceos:complianceos@db:5432/complianceos"
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
    print(f"✓ CORS origins ({len(s.cors_origins)}):")
    for o in s.cors_origins:
        print(f"  - {o}")
    print(f"✓ NVIDIA configured: {s.has_nvidia}")
