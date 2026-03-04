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

# Drop all objects (RDS users don't own the public schema, so drop objects individually)
# Each category uses EXCEPTION handling so permission errors on extension-owned objects
# don't abort the entire block.
PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -U "$DB_USER" -p "$DB_PORT" -d "$DB_NAME" <<'SQL' 2>&1
DO $$
DECLARE
    r RECORD;
    drop_cmd TEXT;
BEGIN
    -- Drop all tables in public schema
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        drop_cmd := 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE';
        BEGIN
            EXECUTE drop_cmd;
        EXCEPTION WHEN insufficient_privilege THEN
            RAISE NOTICE 'Skipping table % (insufficient privilege)', r.tablename;
        END;
    END LOOP;

    -- Drop all sequences (exclude extension-owned)
    FOR r IN (SELECT s.sequencename FROM pg_sequences s
              WHERE s.schemaname = 'public'
              AND NOT EXISTS (
                  SELECT 1 FROM pg_depend d
                  JOIN pg_class c ON c.oid = d.objid
                  WHERE c.relname = s.sequencename AND d.deptype = 'e'
              )) LOOP
        drop_cmd := 'DROP SEQUENCE IF EXISTS public.' || quote_ident(r.sequencename) || ' CASCADE';
        BEGIN
            EXECUTE drop_cmd;
        EXCEPTION WHEN insufficient_privilege THEN
            RAISE NOTICE 'Skipping sequence % (insufficient privilege)', r.sequencename;
        END;
    END LOOP;

    -- Drop all functions/procedures (exclude extension-owned)
    FOR r IN (SELECT p.proname, pg_get_function_identity_arguments(p.oid) AS args
              FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid
              WHERE n.nspname = 'public' AND p.prokind IN ('f', 'p')
              AND NOT EXISTS (
                  SELECT 1 FROM pg_depend d WHERE d.objid = p.oid AND d.deptype = 'e'
              )) LOOP
        drop_cmd := 'DROP FUNCTION IF EXISTS public.' || quote_ident(r.proname) || '(' || r.args || ') CASCADE';
        BEGIN
            EXECUTE drop_cmd;
        EXCEPTION WHEN insufficient_privilege THEN
            RAISE NOTICE 'Skipping function %(%s) (insufficient privilege)', r.proname, r.args;
        END;
    END LOOP;

    -- Drop all custom types/enums (exclude extension-owned)
    FOR r IN (SELECT t.typname FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid
              WHERE n.nspname = 'public' AND t.typtype = 'e'
              AND NOT EXISTS (
                  SELECT 1 FROM pg_depend d WHERE d.objid = t.oid AND d.deptype = 'e'
              )) LOOP
        drop_cmd := 'DROP TYPE IF EXISTS public.' || quote_ident(r.typname) || ' CASCADE';
        BEGIN
            EXECUTE drop_cmd;
        EXCEPTION WHEN insufficient_privilege THEN
            RAISE NOTICE 'Skipping type % (insufficient privilege)', r.typname;
        END;
    END LOOP;
END $$;
SQL

echo "All user-owned objects dropped from public schema."

# Re-run migration to bootstrap
echo "Re-bootstrapping via db_migrate.sh..."
"$SCRIPT_DIR/db_migrate.sh" "$TARGET_ENV" 2>&1

echo "=== Reset complete: $TARGET_ENV ==="
