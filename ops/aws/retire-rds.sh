#!/bin/bash
# The Combine - Retire RDS instance after migrating to Postgres sidecar
#
# Usage:
#   ./ops/aws/retire-rds.sh                        # Dry run (shows what would happen)
#   CONFIRM_RETIRE=yes ./ops/aws/retire-rds.sh     # Actually retire
#
# This script:
#   1. Creates a final snapshot of the RDS instance
#   2. Deletes the RDS instance (with snapshot retention)
#   3. Cleans up Secrets Manager entries for dev/test DB URLs
#   4. Keeps the prod secret (updated to point to sidecar — handled by deploy.yml)
#
# The RDS instance can be restored from the final snapshot if needed.

set -euo pipefail

AWS_REGION="us-east-1"
RDS_INSTANCE="combine-devtest"
SNAPSHOT_ID="combine-devtest-final-$(date +%Y%m%d)"

if [ "${CONFIRM_RETIRE:-}" != "yes" ]; then
    echo "=============================================="
    echo "RDS Retirement Plan (DRY RUN)"
    echo "=============================================="
    echo ""
    echo "This will:"
    echo "  1. Create final snapshot: $SNAPSHOT_ID"
    echo "  2. Delete RDS instance: $RDS_INSTANCE"
    echo "  3. Remove dev/test DB secrets from Secrets Manager"
    echo ""
    echo "The snapshot will be retained indefinitely so you"
    echo "can restore the instance if needed."
    echo ""
    echo "Estimated monthly savings: ~\$20-25 (db.t3.micro + storage)"
    echo ""
    echo "To proceed: CONFIRM_RETIRE=yes $0"
    echo "=============================================="
    exit 0
fi

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ============================================================
# Step 1: Final snapshot
# ============================================================
log "Creating final RDS snapshot: $SNAPSHOT_ID"

aws rds create-db-snapshot \
    --db-instance-identifier "$RDS_INSTANCE" \
    --db-snapshot-identifier "$SNAPSHOT_ID" \
    --region "$AWS_REGION"

log "Waiting for snapshot to complete..."
aws rds wait db-snapshot-completed \
    --db-snapshot-identifier "$SNAPSHOT_ID" \
    --region "$AWS_REGION"

log "Snapshot complete: $SNAPSHOT_ID"

# ============================================================
# Step 2: Delete RDS instance
# ============================================================
log "Deleting RDS instance: $RDS_INSTANCE"

aws rds delete-db-instance \
    --db-instance-identifier "$RDS_INSTANCE" \
    --skip-final-snapshot \
    --region "$AWS_REGION"

log "RDS deletion initiated (takes a few minutes)"

# ============================================================
# Step 3: Clean up dev/test secrets (keep prod)
# ============================================================
log "Cleaning up dev/test DB secrets..."

# Schedule deletion (30-day recovery window by default)
for SECRET in "the-combine/db-dev" "the-combine/db-test" "the-combine/db-devtest-master"; do
    aws secretsmanager delete-secret \
        --secret-id "$SECRET" \
        --recovery-window-in-days 30 \
        --region "$AWS_REGION" 2>/dev/null && \
        log "Scheduled deletion: $SECRET" || \
        log "Secret not found (already deleted?): $SECRET"
done

log "Note: the-combine/db-prod secret kept — deploy.yml no longer references it."
log "You can delete it manually after confirming everything works:"
log "  aws secretsmanager delete-secret --secret-id the-combine/db-prod --recovery-window-in-days 30"

# ============================================================
# Summary
# ============================================================
echo ""
echo "=============================================="
echo "RDS Retired"
echo "=============================================="
echo "Snapshot:  $SNAPSHOT_ID (retained indefinitely)"
echo "Instance:  $RDS_INSTANCE (deleting)"
echo "Secrets:   dev/test scheduled for deletion (30-day recovery)"
echo ""
echo "To restore if needed:"
echo "  aws rds restore-db-instance-from-db-snapshot \\"
echo "    --db-instance-identifier combine-devtest \\"
echo "    --db-snapshot-identifier $SNAPSHOT_ID"
echo "=============================================="
