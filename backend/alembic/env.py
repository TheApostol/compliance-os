"""
ComplianceOS — Alembic async environment configuration.

Configured for async SQLAlchemy (asyncpg driver).
DATABASE_URL is read from the environment at runtime so that the same
alembic.ini works inside Docker Compose and in local dev.
"""

import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Make the backend package importable when alembic is run from backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import Base so that target_metadata is populated.
from app.db.base import Base  # noqa: E402

# Import all model modules so their tables are registered on Base.metadata.
import app.db.models  # noqa: E402, F401
import app.core.audit  # noqa: E402, F401

# Alembic Config object — gives access to values in alembic.ini.
config = context.config

# Set up Python logging from alembic.ini config.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata object for 'autogenerate' support.
target_metadata = Base.metadata

# Read the database URL from the environment at runtime.
# This allows the same alembic.ini to work in Docker and local dev.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://complianceos:complianceos@localhost:5432/complianceos",
)


# ── Offline mode ───────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection required).

    This emits the SQL to stdout/a file rather than executing it.
    Useful for generating SQL scripts for DBA review.
    """
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode ────────────────────────────────────────────────────────────────
def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(DATABASE_URL, echo=False)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using an async engine."""
    asyncio.run(run_async_migrations())


# ── Entry point ────────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
