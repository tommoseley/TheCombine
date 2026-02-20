#!/usr/bin/env bash
# =============================================================================
# Database reset script — drops and recreates all tables.
# DESTRUCTIVE: Requires CONFIRM_ENV=<target> to proceed.
#
# Usage:
#   CONFIRM_ENV=dev ops/scripts/db_reset.sh dev
#   CONFIRM_ENV=test ops/scripts/db_reset.sh test
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source the guard
source "$SCRIPT_DIR/db_destructive_guard.sh"

if [[ $# -lt 1 ]]; then
    echo "Usage: CONFIRM_ENV=<env> db_reset.sh <dev|test>" >&2
    exit 2
fi

TARGET_ENV="$1"

if [[ "$TARGET_ENV" != "dev" && "$TARGET_ENV" != "test" ]]; then
    echo "ERROR: Target must be 'dev' or 'test'" >&2
    exit 2
fi

# Require confirmation
require_confirmation "$TARGET_ENV" "DROP all tables and recreate schema"

# Get DATABASE_URL
DATABASE_URL=$("$SCRIPT_DIR/db_connect.sh" "$TARGET_ENV" 2>/dev/null | tail -1)
export DATABASE_URL

echo "Resetting $TARGET_ENV database..."

# Extract connection parts
DB_HOST=$(echo "$DATABASE_URL" | python3 -c "from urllib.parse import urlparse; import sys; u=urlparse(sys.stdin.read().strip()); print(u.hostname)")
DB_PORT=$(echo "$DATABASE_URL" | python3 -c "from urllib.parse import urlparse; import sys; u=urlparse(sys.stdin.read().strip()); print(u.port or 5432)")
DB_NAME=$(echo "$DATABASE_URL" | python3 -c "from urllib.parse import urlparse; import sys; u=urlparse(sys.stdin.read().strip()); print(u.path.lstrip('/'))")
DB_USER=$(echo "$DATABASE_URL" | python3 -c "from urllib.parse import urlparse; import sys; u=urlparse(sys.stdin.read().strip()); print(u.username)")
DB_PASS=$(echo "$DATABASE_URL" | python3 -c "from urllib.parse import urlparse; import sys; u=urlparse(sys.stdin.read().strip()); print(u.password)")

# Drop all tables
PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -U "$DB_USER" -p "$DB_PORT" -d "$DB_NAME" -c \
    "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO $DB_USER;" 2>&1

echo "Schema dropped and recreated."

# Re-run migration to bootstrap
echo "Re-bootstrapping via db_migrate.sh..."
"$SCRIPT_DIR/db_migrate.sh" "$TARGET_ENV" 2>&1

echo "=== Reset complete: $TARGET_ENV ==="
