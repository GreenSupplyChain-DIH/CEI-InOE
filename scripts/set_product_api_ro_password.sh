#!/usr/bin/env bash
# Creates (if missing) the read-only role product_api_ro and sets its password
# on a PostgreSQL server reachable from this machine (no Docker required).
#
# Usage:
#   PRODUCT_API_RO_PASSWORD='secret' PGUSER=postgres PGPASSWORD=admin-pw \
#     ./scripts/set_product_api_ro_password.sh
#
# Connection uses the standard libpq variables: PGHOST (default localhost),
# PGPORT (default 5432), PGUSER, PGPASSWORD, PGDATABASE (default ocei).
set -euo pipefail

: "${PRODUCT_API_RO_PASSWORD:?Set PRODUCT_API_RO_PASSWORD}"
export PGHOST="${PGHOST:-localhost}"
export PGPORT="${PGPORT:-5432}"
export PGUSER="${PGUSER:-postgres}"
export PGDATABASE="${PGDATABASE:-ocei4}"

psql -v ON_ERROR_STOP=1 -v pw="$PRODUCT_API_RO_PASSWORD" <<'SQL'
SELECT NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'product_api_ro') AS missing \gset
\if :missing
  CREATE ROLE product_api_ro LOGIN;
\endif
ALTER ROLE product_api_ro PASSWORD :'pw';
SQL

echo "Password set for product_api_ro on ${PGHOST}:${PGPORT}/${PGDATABASE}."
