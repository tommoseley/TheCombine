#!/usr/bin/env bash
# =============================================================================
# Dump canonical schema from a running database environment.
#
# Captures DDL (all tables, indexes, constraints, functions, triggers)
# plus seed data (alembic_version stamp + document_types registry),
# so the dump can bootstrap a fresh DB that's ready to run.
#
# Output replaces ops/db/schema.sql.
#
# Usage:
#   ops/scripts/db_dump_schema.sh prod    # Dump from production (typical)
#   ops/scripts/db_dump_schema.sh dev     # Dump from dev
#   ops/scripts/db_dump_schema.sh test    # Dump from test
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_FILE="$REPO_ROOT/ops/db/schema.sql"

if [[ $# -lt 1 ]]; then
    echo "Usage: db_dump_schema.sh <prod|dev|test>" >&2
    exit 2
fi

SOURCE_ENV="$1"

# ---------------------------------------------------------------------------
# Get credentials
# ---------------------------------------------------------------------------
echo "=== Dumping schema from $SOURCE_ENV ==="

# Get DATABASE_URL (works for dev/test/prod via db_connect.sh)
DATABASE_URL=$("$SCRIPT_DIR/db_connect.sh" "$SOURCE_ENV" 2>/dev/null | tail -1)

if [[ -z "$DATABASE_URL" || "$DATABASE_URL" != postgresql://* ]]; then
    echo "ERROR: Failed to retrieve DATABASE_URL for $SOURCE_ENV" >&2
    exit 1
fi

# Extract connection parts
DB_HOST=$(echo "$DATABASE_URL" | python3 -c "from urllib.parse import urlparse; import sys; u=urlparse(sys.stdin.read().strip()); print(u.hostname)")
DB_PORT=$(echo "$DATABASE_URL" | python3 -c "from urllib.parse import urlparse; import sys; u=urlparse(sys.stdin.read().strip()); print(u.port or 5432)")
DB_NAME=$(echo "$DATABASE_URL" | python3 -c "from urllib.parse import urlparse; import sys; u=urlparse(sys.stdin.read().strip()); print(u.path.lstrip('/'))")
DB_USER=$(echo "$DATABASE_URL" | python3 -c "from urllib.parse import urlparse; import sys; u=urlparse(sys.stdin.read().strip()); print(u.username)")
DB_PASS=$(echo "$DATABASE_URL" | python3 -c "from urllib.parse import urlparse; import sys; u=urlparse(sys.stdin.read().strip()); print(u.password)")

echo "  Host: $DB_HOST"
echo "  Database: $DB_NAME"

# ---------------------------------------------------------------------------
# Dump schema (DDL only) + alembic_version data
# ---------------------------------------------------------------------------
echo "  Dumping schema..."

# Prefer pg_dump >= 18 to match RDS server version
PG_DUMP="pg_dump"
if [[ -x /usr/lib/postgresql/18/bin/pg_dump ]]; then
    PG_DUMP="/usr/lib/postgresql/18/bin/pg_dump"
fi
echo "  Using: $($PG_DUMP --version)"

{
    echo "-- Canonical schema dump from $SOURCE_ENV"
    echo "-- Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "-- Source: $DB_NAME@$DB_HOST"
    echo ""

    # Schema-only dump (all DDL: tables, indexes, constraints, functions, triggers)
    PGPASSWORD="$DB_PASS" "$PG_DUMP" \
        -h "$DB_HOST" -U "$DB_USER" -p "$DB_PORT" -d "$DB_NAME" \
        --schema-only \
        --no-owner \
        --no-privileges \
        --no-comments \
        2>/dev/null

    echo ""
    echo "-- Seed data: alembic_version + document_types (required for bootstrap)"

    # Data-only dump of bootstrap-essential tables
    PGPASSWORD="$DB_PASS" "$PG_DUMP" \
        -h "$DB_HOST" -U "$DB_USER" -p "$DB_PORT" -d "$DB_NAME" \
        --data-only \
        --table=alembic_version \
        --table=document_types \
        --no-owner \
        --no-privileges \
        2>/dev/null

} > "$OUTPUT_FILE"

# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------
LINE_COUNT=$(wc -l < "$OUTPUT_FILE")
TABLE_COUNT=$(grep -c "CREATE TABLE" "$OUTPUT_FILE" || true)
ALEMBIC_VER=$(grep -A1 "COPY public.alembic_version" "$OUTPUT_FILE" | tail -1 || echo "(none)")

echo ""
echo "  Output: $OUTPUT_FILE"
echo "  Lines: $LINE_COUNT"
echo "  Tables: $TABLE_COUNT"
echo "  Alembic stamp: $ALEMBIC_VER"
echo ""
echo "=== Schema dump complete ==="
echo ""
echo "Next steps:"
echo "  1. Review the dump: less $OUTPUT_FILE"
echo "  2. Commit: git add ops/db/schema.sql"
echo "  3. Reset dev: CONFIRM_ENV=dev ops/scripts/db_reset.sh dev"
