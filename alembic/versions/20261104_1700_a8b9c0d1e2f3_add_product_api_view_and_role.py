"""Add Product API read-only view and database role.

Creates the purpose-built view ``product_energy_hourly_v1`` (ts, energy_kwh,
datasource_id only) and the least-privileged login role ``product_api_ro`` that
may ``SELECT`` from that view and nothing else.

The role password is never stored in this file. Set it either by exporting
``PRODUCT_API_DB_PASSWORD`` when running ``alembic upgrade`` or afterwards with
``ALTER ROLE product_api_ro PASSWORD '...'``. Without a password the role cannot
log in with password authentication.

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-11-04 17:00:00.000000+00:00
"""
import os
from typing import Sequence, Union

from alembic import op

revision: str = 'a8b9c0d1e2f3'
down_revision: Union[str, None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROLE = 'product_api_ro'
VIEW = 'product_energy_hourly_v1'


def upgrade() -> None:
    op.execute(
        f"""
        CREATE OR REPLACE VIEW {VIEW} AS
        SELECT ts, energy_kwh, datasource_id
        FROM fact_energy_hourly
        WHERE datasource_id IS NOT NULL
        """
    )

    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{ROLE}') THEN
                CREATE ROLE {ROLE} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
            END IF;
        END
        $$;
        """
    )

    password = os.getenv('PRODUCT_API_DB_PASSWORD')
    if password:
        # DDL cannot use bind parameters; escape the literal.
        escaped = password.replace("'", "''")
        op.execute(f"ALTER ROLE {ROLE} PASSWORD '{escaped}'")

    # The view runs with its owner's privileges, so the role needs no table access.
    op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {ROLE}")
    op.execute(f"GRANT USAGE ON SCHEMA public TO {ROLE}")
    op.execute(
        f"""
        DO $$
        BEGIN
            EXECUTE format('GRANT CONNECT ON DATABASE %I TO {ROLE}', current_database());
        END
        $$;
        """
    )
    op.execute(f"GRANT SELECT ON {VIEW} TO {ROLE}")


def downgrade() -> None:
    op.execute(f"DROP VIEW IF EXISTS {VIEW}")
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{ROLE}') THEN
                DROP OWNED BY {ROLE};
                DROP ROLE {ROLE};
            END IF;
        END
        $$;
        """
    )
