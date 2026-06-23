"""Enforce audit_log INSERT-ONLY at the DB level (T0.4)

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-23

Adds a BEFORE UPDATE/DELETE trigger on audit_log that raises an exception
unconditionally. Table-owner GRANT/REVOKE alone does not work here — Postgres
table owners bypass privilege checks, and the app currently connects as the
owning role — so a trigger is the only mechanism that blocks mutation
regardless of which role issues the statement. Also provisions a
least-privilege `complianceos_audit_logger` role (SELECT, INSERT only) for
deployments that want to point the app's audit-write connection at a
non-owner role.

Set AUDIT_LOGGER_DB_PASSWORD before running this migration to give the role
a login password; if unset, the role is created without one (NOLOGIN-by-
password, must be set later via `ALTER ROLE ... PASSWORD`). Never hardcode
a default password here.
"""
import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

AUDIT_LOGGER_PASSWORD_ENV = "AUDIT_LOGGER_DB_PASSWORD"


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log is insert-only: % is not permitted', TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_audit_log_insert_only ON audit_log;")
    op.execute(
        """
        CREATE TRIGGER trg_audit_log_insert_only
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation();
        """
    )

    bind = op.get_bind()
    role_exists = bind.execute(
        sa.text("SELECT 1 FROM pg_roles WHERE rolname = 'complianceos_audit_logger'")
    ).first() is not None
    password = os.environ.get(AUDIT_LOGGER_PASSWORD_ENV)

    if not role_exists:
        if password:
            bind.execute(
                sa.text("CREATE ROLE complianceos_audit_logger LOGIN PASSWORD :pwd").bindparams(pwd=password)
            )
        else:
            bind.execute(sa.text("CREATE ROLE complianceos_audit_logger LOGIN"))
    elif password:
        bind.execute(
            sa.text("ALTER ROLE complianceos_audit_logger PASSWORD :pwd").bindparams(pwd=password)
        )

    op.execute("GRANT SELECT, INSERT ON audit_log TO complianceos_audit_logger;")
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM complianceos_audit_logger;")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE audit_log_id_seq TO complianceos_audit_logger;")


def downgrade() -> None:
    op.execute("REVOKE ALL ON audit_log FROM complianceos_audit_logger;")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_log_insert_only ON audit_log;")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_log_mutation();")
