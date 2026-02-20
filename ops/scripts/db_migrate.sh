#!/usr/bin/env bash
# =============================================================================
# WS-AWS-DB-004: Migration script for DEV and TEST databases
#
# Retrieves credentials via db_connect.sh, runs Alembic migrations,
# and performs a smoke query to verify tables exist.
#
# Usage:
#   ops/scripts/db_migrate.sh dev          # Migrate DEV
#   ops/scripts/db_migrate.sh test         # Migrate TEST
#   ops/scripts/db_migrate.sh dev --seed   # Migrate + seed DEV
#
# Exit codes:
#   0 = success
#   1 = migration/seed failure
#   2 = usage error
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
usage() {
    echo "Usage: db_migrate.sh <dev|test> [--seed]" >&2
    echo "" >&2
    echo "Runs Alembic migrations against the target environment." >&2
    echo "  --seed   Also run seed data after migration" >&2
    exit 2
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
if [[ $# -lt 1 ]]; then
    usage
fi

TARGET_ENV="$1"
shift

DO_SEED=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --seed) DO_SEED=true; shift ;;
        *)      echo "ERROR: Unknown option: $1" >&2; usage ;;
    esac
done

# Validate target
if [[ "$TARGET_ENV" != "dev" && "$TARGET_ENV" != "test" ]]; then
    echo "ERROR: Target must be 'dev' or 'test', got '$TARGET_ENV'" >&2
    echo "Production migrations are not permitted via this script." >&2
    exit 2
fi

# Map target to ENVIRONMENT value
declare -A ENV_MAP=( [dev]="dev_aws" [test]="test_aws" )
ENVIRONMENT_VALUE="${ENV_MAP[$TARGET_ENV]}"

# ---------------------------------------------------------------------------
# Production guard
# ---------------------------------------------------------------------------
if [[ "${ENVIRONMENT:-}" == "production" || "${ENVIRONMENT:-}" == "staging" ]]; then
    echo "ERROR: This script must not be run in production or staging." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Step 1: Get DATABASE_URL from connection script
# ---------------------------------------------------------------------------
echo "=== Retrieving $TARGET_ENV connection string ==="
DATABASE_URL=$("$SCRIPT_DIR/db_connect.sh" "$TARGET_ENV" --check 2>/dev/null | tail -1)

if [[ -z "$DATABASE_URL" || "$DATABASE_URL" != postgresql://* ]]; then
    echo "ERROR: Failed to retrieve DATABASE_URL for $TARGET_ENV" >&2
    echo "Run: ops/scripts/db_connect.sh $TARGET_ENV --check" >&2
    exit 1
fi

echo "  Connected to $TARGET_ENV"
export DATABASE_URL
export ENVIRONMENT="$ENVIRONMENT_VALUE"

# ---------------------------------------------------------------------------
# Step 2: Run Alembic migrations
# ---------------------------------------------------------------------------
echo ""
echo "=== Running Alembic migrations on $TARGET_ENV ==="
cd "$REPO_ROOT"

# Activate venv if present
if [[ -f "$REPO_ROOT/venv/bin/activate" ]]; then
    source "$REPO_ROOT/venv/bin/activate"
fi

# Extract connection parts for psql operations
DB_HOST_TMP=$(echo "$DATABASE_URL" | python3 -c "from urllib.parse import urlparse; import sys; u=urlparse(sys.stdin.read().strip()); print(u.hostname)")
DB_PORT_TMP=$(echo "$DATABASE_URL" | python3 -c "from urllib.parse import urlparse; import sys; u=urlparse(sys.stdin.read().strip()); print(u.port or 5432)")
DB_NAME_TMP=$(echo "$DATABASE_URL" | python3 -c "from urllib.parse import urlparse; import sys; u=urlparse(sys.stdin.read().strip()); print(u.path.lstrip('/'))")
DB_USER_TMP=$(echo "$DATABASE_URL" | python3 -c "from urllib.parse import urlparse; import sys; u=urlparse(sys.stdin.read().strip()); print(u.username)")
DB_PASS_TMP=$(echo "$DATABASE_URL" | python3 -c "from urllib.parse import urlparse; import sys; u=urlparse(sys.stdin.read().strip()); print(u.password)")

# Check if this is an empty database (no tables yet)
TABLE_CHECK=$(PGPASSWORD="$DB_PASS_TMP" psql -h "$DB_HOST_TMP" -U "$DB_USER_TMP" -p "$DB_PORT_TMP" -d "$DB_NAME_TMP" -t -c \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';" 2>/dev/null | tr -d ' ')

if [[ "$TABLE_CHECK" == "0" || -z "$TABLE_CHECK" ]]; then
    echo "  Empty database detected — bootstrapping base schema via init_db.py"
    python "$REPO_ROOT/ops/db/init_db.py" 2>&1
    echo "  Base schema bootstrapped"
    # Stamp alembic to latest so migrations don't try to replay
    python -m alembic stamp head 2>&1
    echo "  Alembic stamped to head"
else
    echo "  Existing tables found ($TABLE_CHECK) — running incremental migrations"
    python -m alembic upgrade head 2>&1
fi
echo "  Migrations complete"

# ---------------------------------------------------------------------------
# Step 3: Smoke query — verify expected tables exist
# ---------------------------------------------------------------------------
echo ""
echo "=== Smoke query: verifying tables ==="

# Reuse connection parts from earlier extraction
DB_HOST="$DB_HOST_TMP"
DB_PORT="$DB_PORT_TMP"
DB_NAME="$DB_NAME_TMP"
DB_USER="$DB_USER_TMP"
DB_PASS="$DB_PASS_TMP"

TABLE_COUNT=$(PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -U "$DB_USER" -p "$DB_PORT" -d "$DB_NAME" -t -c \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';")
TABLE_COUNT=$(echo "$TABLE_COUNT" | tr -d ' ')

echo "  Tables in $TARGET_ENV: $TABLE_COUNT"

# Verify key tables exist
KEY_TABLES="documents document_types alembic_version"
for tbl in $KEY_TABLES; do
    EXISTS=$(PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -U "$DB_USER" -p "$DB_PORT" -d "$DB_NAME" -t -c \
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='$tbl');")
    EXISTS=$(echo "$EXISTS" | tr -d ' ')
    if [[ "$EXISTS" == "t" ]]; then
        printf "  %-25s OK\n" "$tbl"
    else
        echo "  $tbl MISSING" >&2
        exit 1
    fi
done

# ---------------------------------------------------------------------------
# Step 4: Optional seed (with env guard)
# ---------------------------------------------------------------------------
if [[ "$DO_SEED" == "true" ]]; then
    echo ""
    echo "=== Seeding $TARGET_ENV ==="

    # Env guard: verify ENVIRONMENT matches target
    if [[ "$ENVIRONMENT" != "$ENVIRONMENT_VALUE" ]]; then
        echo "ERROR: ENVIRONMENT mismatch. Expected '$ENVIRONMENT_VALUE', got '$ENVIRONMENT'" >&2
        echo "Cannot seed $TARGET_ENV with wrong environment set." >&2
        exit 1
    fi

    # Run seed scripts (idempotent)
    if [[ -f "$REPO_ROOT/ops/db/seed_data.py" ]]; then
        python "$REPO_ROOT/ops/db/seed_data.py" 2>&1
        echo "  seed_data.py complete"
    fi

    if [[ -f "$REPO_ROOT/ops/db/seed_acceptance_config.py" ]]; then
        python "$REPO_ROOT/ops/db/seed_acceptance_config.py" 2>&1
        echo "  seed_acceptance_config.py complete"
    fi

    echo "  Seeding complete"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "==========================================="
echo "  MIGRATION COMPLETE: $TARGET_ENV"
echo "==========================================="
echo "  Tables: $TABLE_COUNT"
echo "  Environment: $ENVIRONMENT_VALUE"
if [[ "$DO_SEED" == "true" ]]; then
    echo "  Seeded: yes"
fi
echo "==========================================="
