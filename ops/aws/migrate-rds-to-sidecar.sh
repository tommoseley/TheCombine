#!/bin/bash
# The Combine - Migrate data from RDS to Fargate Postgres sidecar
#
# Usage:
#   ./ops/aws/migrate-rds-to-sidecar.sh          # Dry run
#   ./ops/aws/migrate-rds-to-sidecar.sh --apply   # Execute migration
#
# Prerequisites:
#   - The new multi-container task must already be running (setup-efs-sidecar.sh)
#   - pg_dump and psql must be installed locally
#   - AWS CLI configured
#   - RDS security group allows your current IP
#
# Strategy:
#   1. pg_dump from RDS (production database)
#   2. Start the new ECS task with postgres sidecar
#   3. pg_restore to the sidecar postgres via ECS Exec
#   4. Verify data integrity

set -euo pipefail

AWS_REGION="us-east-1"
ECS_CLUSTER="the-combine-cluster"
ECS_SERVICE="the-combine-service"
DUMP_FILE="/tmp/combine-prod-dump.sql"

DRY_RUN=true
if [ "${1:-}" = "--apply" ]; then
    DRY_RUN=false
fi

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ============================================================
# Step 1: Get RDS connection details from Secrets Manager
# ============================================================
log "=== Step 1: Get RDS credentials ==="

if $DRY_RUN; then
    log "[DRY RUN] Would fetch DATABASE_URL from the-combine/db-prod"
    RDS_URL="postgresql://user:pass@combine-devtest.cyqzjxl9c9jd.us-east-1.rds.amazonaws.com:5432/combine_prod"
else
    RDS_URL=$(aws secretsmanager get-secret-value \
        --secret-id the-combine/db-prod \
        --query 'SecretString' --output text \
        --region "$AWS_REGION" | jq -r '.DATABASE_URL')
    log "Got RDS URL (host: $(echo "$RDS_URL" | sed 's/.*@\(.*\):.*/\1/'))"
fi

# ============================================================
# Step 2: Dump production data from RDS
# ============================================================
log "=== Step 2: Dump from RDS ==="

if $DRY_RUN; then
    log "[DRY RUN] Would run: pg_dump --no-owner --no-acl --clean --if-exists -f $DUMP_FILE"
else
    log "Dumping production database..."
    pg_dump "$RDS_URL" \
        --no-owner \
        --no-acl \
        --clean \
        --if-exists \
        -f "$DUMP_FILE"

    DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
    DUMP_TABLES=$(grep -c "^CREATE TABLE" "$DUMP_FILE" || true)
    log "Dump complete: $DUMP_SIZE, ~$DUMP_TABLES tables"
fi

# ============================================================
# Step 3: Enable ECS Exec on the service (for psql access)
# ============================================================
log "=== Step 3: Enable ECS Exec ==="

if $DRY_RUN; then
    log "[DRY RUN] Would enable ECS Exec on the service"
else
    aws ecs update-service \
        --cluster "$ECS_CLUSTER" \
        --service "$ECS_SERVICE" \
        --enable-execute-command \
        --region "$AWS_REGION" > /dev/null
    log "ECS Exec enabled. Waiting for new task to launch (60s)..."
    sleep 60
fi

# ============================================================
# Step 4: Find the running task
# ============================================================
log "=== Step 4: Find running task ==="

if $DRY_RUN; then
    log "[DRY RUN] Would find running task ARN"
    TASK_ARN="arn:aws:ecs:us-east-1:303985543798:task/the-combine-cluster/PLACEHOLDER"
else
    TASK_ARN=$(aws ecs list-tasks \
        --cluster "$ECS_CLUSTER" \
        --service-name "$ECS_SERVICE" \
        --desired-status RUNNING \
        --query 'taskArns[0]' --output text \
        --region "$AWS_REGION")
    log "Running task: $TASK_ARN"
fi

# ============================================================
# Step 5: Restore dump to sidecar Postgres
# ============================================================
log "=== Step 5: Restore to sidecar ==="

if $DRY_RUN; then
    log "[DRY RUN] Would restore dump via ECS Exec into postgres container"
    log "[DRY RUN] Command: aws ecs execute-command --cluster $ECS_CLUSTER --task TASK --container postgres --interactive --command 'psql -U combine -d combine'"
else
    # Pipe the dump file through ECS Exec
    # Note: For large dumps, consider using S3 as intermediary
    log "Restoring dump to sidecar postgres..."
    log "This uses ECS Exec to pipe SQL into the postgres container."

    # First check connectivity
    aws ecs execute-command \
        --cluster "$ECS_CLUSTER" \
        --task "$TASK_ARN" \
        --container postgres \
        --interactive \
        --command "psql -U combine -d combine -c 'SELECT 1'" \
        --region "$AWS_REGION"

    log "Postgres container is reachable. Starting restore..."

    # For a small database, pipe directly. For large ones, upload to S3 first.
    # The Combine's DB is small enough for direct pipe.
    cat "$DUMP_FILE" | aws ecs execute-command \
        --cluster "$ECS_CLUSTER" \
        --task "$TASK_ARN" \
        --container postgres \
        --interactive \
        --command "psql -U combine -d combine" \
        --region "$AWS_REGION"

    log "Restore complete"
fi

# ============================================================
# Step 6: Verify data integrity
# ============================================================
log "=== Step 6: Verify ==="

if $DRY_RUN; then
    log "[DRY RUN] Would verify table counts match between RDS and sidecar"
else
    log "Verifying data integrity..."

    # Count tables in sidecar
    SIDECAR_TABLES=$(aws ecs execute-command \
        --cluster "$ECS_CLUSTER" \
        --task "$TASK_ARN" \
        --container postgres \
        --interactive \
        --command "psql -U combine -d combine -t -c \"SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'\"" \
        --region "$AWS_REGION" | tr -d ' ')

    # Count tables in RDS
    RDS_TABLES=$(psql "$RDS_URL" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'" | tr -d ' ')

    log "RDS tables: $RDS_TABLES"
    log "Sidecar tables: $SIDECAR_TABLES"

    if [ "$RDS_TABLES" = "$SIDECAR_TABLES" ]; then
        log "Table counts match"
    else
        log "WARNING: Table count mismatch! Manual verification needed."
    fi

    # Verify app health
    log "Checking app health endpoint..."
    sleep 10
    HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "https://www.thecombine.ai/health" --max-time 10 || echo "000")
    log "Health check: HTTP $HEALTH"
fi

# ============================================================
# Summary
# ============================================================
echo ""
echo "=================================================="
echo "Migration Summary"
echo "=================================================="
if $DRY_RUN; then
    echo "DRY RUN complete. Run with --apply to execute."
else
    echo "Migration complete."
    echo "  Dump file: $DUMP_FILE (keep as backup)"
    echo ""
    echo "Next steps:"
    echo "  1. Verify the app at https://www.thecombine.ai"
    echo "  2. Test a few document operations"
    echo "  3. Once confident, retire RDS: ops/aws/retire-rds.sh"
fi
echo "=================================================="
