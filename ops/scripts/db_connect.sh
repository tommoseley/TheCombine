#!/usr/bin/env bash
# =============================================================================
# WS-AWS-DB-002: Connection script for DEV and TEST databases
#
# Retrieves credentials from AWS Secrets Manager and prints the DATABASE_URL.
# Optionally runs a connectivity check via pg_isready.
#
# Usage:
#   ops/scripts/db_connect.sh dev          # Print DEV DATABASE_URL
#   ops/scripts/db_connect.sh test         # Print TEST DATABASE_URL
#   ops/scripts/db_connect.sh dev --check  # Print URL + verify connectivity
#   ops/scripts/db_connect.sh dev --psql   # Open interactive psql session
#
# Environment:
#   Requires AWS CLI configured with permissions to read Secrets Manager.
#   No credentials are hardcoded — all retrieved at runtime.
#
# Exit codes:
#   0 = success
#   1 = connection/retrieval failure
#   2 = usage error
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
declare -A SECRET_NAMES=(
    [dev]="the-combine/db-dev"
    [test]="the-combine/db-test"
)
REGION="us-east-1"

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
usage() {
    echo "Usage: db_connect.sh <dev|test> [--check] [--psql]" >&2
    echo "" >&2
    echo "Options:" >&2
    echo "  --check   Verify database connectivity after retrieving URL" >&2
    echo "  --psql    Open interactive psql session to the database" >&2
    echo "" >&2
    echo "Prints DATABASE_URL to stdout. All other output goes to stderr." >&2
    exit 2
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
if [[ $# -lt 1 ]]; then
    usage
fi

ENV_NAME="$1"
shift

DO_CHECK=false
DO_PSQL=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --check) DO_CHECK=true; shift ;;
        --psql)  DO_PSQL=true; shift ;;
        *)       echo "ERROR: Unknown option: $1" >&2; usage ;;
    esac
done

# Validate environment name
if [[ -z "${SECRET_NAMES[$ENV_NAME]+x}" ]]; then
    echo "ERROR: Unknown environment '$ENV_NAME'. Must be one of: ${!SECRET_NAMES[*]}" >&2
    exit 2
fi

SECRET_NAME="${SECRET_NAMES[$ENV_NAME]}"

# ---------------------------------------------------------------------------
# Step 1: Check AWS CLI is available
# ---------------------------------------------------------------------------
if ! command -v aws &>/dev/null; then
    echo "ERROR: AWS CLI not found. Install it: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Step 2: Retrieve credentials from Secrets Manager
# ---------------------------------------------------------------------------
echo "Retrieving credentials for '$ENV_NAME' from Secrets Manager..." >&2

SECRET_JSON=$(aws secretsmanager get-secret-value \
    --secret-id "$SECRET_NAME" \
    --query 'SecretString' \
    --output text \
    --region "$REGION" 2>&1) || {
    echo "ERROR: Failed to retrieve secret '$SECRET_NAME' from Secrets Manager." >&2
    echo "Check that:" >&2
    echo "  1. AWS CLI is configured with valid credentials (aws sts get-caller-identity)" >&2
    echo "  2. You have secretsmanager:GetSecretValue permission" >&2
    echo "  3. Secret '$SECRET_NAME' exists in region $REGION" >&2
    exit 1
}

# ---------------------------------------------------------------------------
# Step 3: Extract DATABASE_URL
# ---------------------------------------------------------------------------
DATABASE_URL=$(echo "$SECRET_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['DATABASE_URL'])" 2>/dev/null) || {
    echo "ERROR: Secret '$SECRET_NAME' does not contain a DATABASE_URL field." >&2
    echo "Expected JSON with key 'DATABASE_URL'. Got:" >&2
    echo "$SECRET_JSON" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" >&2 2>/dev/null
    exit 1
}

# ---------------------------------------------------------------------------
# Step 4: Connectivity check (optional)
# ---------------------------------------------------------------------------
if [[ "$DO_CHECK" == "true" || "$DO_PSQL" == "true" ]]; then
    # Extract host and port for pg_isready
    DB_HOST=$(echo "$SECRET_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['host'])")
    DB_PORT=$(echo "$SECRET_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['port'])")
    DB_NAME=$(echo "$SECRET_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['dbname'])")
    DB_USER=$(echo "$SECRET_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['username'])")
    DB_PASS=$(echo "$SECRET_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['password'])")

    echo "Checking connectivity to $DB_HOST:$DB_PORT/$DB_NAME..." >&2

    if command -v pg_isready &>/dev/null; then
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -U "$DB_USER" -t 5 >&2; then
            echo "Connection OK." >&2
        else
            echo "ERROR: Database is not accepting connections." >&2
            echo "Check that:" >&2
            echo "  1. RDS instance is running (aws rds describe-db-instances --db-instance-identifier combine-devtest)" >&2
            echo "  2. Your IP is in the security group (current IP: $(curl -s https://checkip.amazonaws.com))" >&2
            echo "  3. Network allows outbound connections on port $DB_PORT" >&2
            exit 1
        fi
    else
        echo "pg_isready not found — skipping connectivity check" >&2
    fi

    # Open psql session if requested
    if [[ "$DO_PSQL" == "true" ]]; then
        echo "Opening psql session..." >&2
        PGPASSWORD="$DB_PASS" exec psql -h "$DB_HOST" -U "$DB_USER" -p "$DB_PORT" -d "$DB_NAME"
    fi
fi

# ---------------------------------------------------------------------------
# Output: DATABASE_URL to stdout (only useful output on stdout)
# ---------------------------------------------------------------------------
echo "$DATABASE_URL"
