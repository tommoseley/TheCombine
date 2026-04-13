#!/bin/bash
# The Combine - Set up AWS Backup for EFS (Postgres data)
#
# Usage:
#   ./ops/aws/setup-efs-backup.sh                    # Dry run
#   ./ops/aws/setup-efs-backup.sh --apply fs-xxxxx   # Create backup plan for given EFS ID
#
# Creates:
#   - Backup vault (combine-pgdata-vault)
#   - Backup plan (daily at 3am UTC, 7-day retention)
#   - Backup selection targeting the EFS filesystem
#   - IAM role for AWS Backup

set -euo pipefail

AWS_REGION="us-east-1"
ACCOUNT_ID="303985543798"
VAULT_NAME="combine-pgdata-vault"
PLAN_NAME="combine-pgdata-daily"
ROLE_NAME="combine-backup-role"

DRY_RUN=true
EFS_ID=""

if [ "${1:-}" = "--apply" ]; then
    DRY_RUN=false
    EFS_ID="${2:-}"
    if [ -z "$EFS_ID" ]; then
        echo "Usage: $0 --apply <efs-filesystem-id>"
        exit 1
    fi
fi

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ============================================================
# Step 1: Create IAM role for AWS Backup
# ============================================================
log "=== Step 1: Backup IAM Role ==="

TRUST_POLICY='{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "backup.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }
    ]
}'

if $DRY_RUN; then
    log "[DRY RUN] Would create IAM role: $ROLE_NAME"
else
    # Create role (ignore if exists)
    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document "$TRUST_POLICY" \
        --region "$AWS_REGION" 2>/dev/null || log "Role already exists"

    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup" 2>/dev/null || true

    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForRestores" 2>/dev/null || true

    log "Backup IAM role ready"
fi

# ============================================================
# Step 2: Create backup vault
# ============================================================
log "=== Step 2: Backup Vault ==="

if $DRY_RUN; then
    log "[DRY RUN] Would create backup vault: $VAULT_NAME"
else
    aws backup create-backup-vault \
        --backup-vault-name "$VAULT_NAME" \
        --region "$AWS_REGION" 2>/dev/null || log "Vault already exists"
    log "Backup vault ready: $VAULT_NAME"
fi

# ============================================================
# Step 3: Create backup plan (daily, 7-day retention)
# ============================================================
log "=== Step 3: Backup Plan ==="

BACKUP_PLAN='{
    "BackupPlanName": "'"$PLAN_NAME"'",
    "Rules": [
        {
            "RuleName": "daily-3am-utc",
            "TargetBackupVaultName": "'"$VAULT_NAME"'",
            "ScheduleExpression": "cron(0 3 * * ? *)",
            "StartWindowMinutes": 60,
            "CompletionWindowMinutes": 120,
            "Lifecycle": {
                "DeleteAfterDays": 7
            }
        }
    ]
}'

if $DRY_RUN; then
    log "[DRY RUN] Would create backup plan: daily at 3am UTC, 7-day retention"
    PLAN_ID="plan-PLACEHOLDER"
else
    PLAN_ID=$(aws backup create-backup-plan \
        --backup-plan "$BACKUP_PLAN" \
        --query 'BackupPlanId' --output text \
        --region "$AWS_REGION")
    log "Created backup plan: $PLAN_ID"
fi

# ============================================================
# Step 4: Assign EFS to the backup plan
# ============================================================
log "=== Step 4: Backup Selection ==="

if $DRY_RUN; then
    log "[DRY RUN] Would assign EFS filesystem to backup plan"
else
    SELECTION='{
        "SelectionName": "combine-efs-pgdata",
        "IamRoleArn": "arn:aws:iam::'"$ACCOUNT_ID"':role/'"$ROLE_NAME"'",
        "Resources": [
            "arn:aws:elasticfilesystem:'"$AWS_REGION"':'"$ACCOUNT_ID"':file-system/'"$EFS_ID"'"
        ]
    }'

    aws backup create-backup-selection \
        --backup-plan-id "$PLAN_ID" \
        --backup-selection "$SELECTION" \
        --region "$AWS_REGION" > /dev/null
    log "EFS assigned to backup plan"
fi

# ============================================================
# Summary
# ============================================================
echo ""
echo "=================================================="
echo "Backup Setup Summary"
echo "=================================================="
echo "Vault:     $VAULT_NAME"
echo "Plan:      $PLAN_NAME"
echo "Schedule:  Daily at 3:00 AM UTC"
echo "Retention: 7 days"
echo "Cost:      ~\$0.05/GB/month (pennies for your data volume)"
echo ""
if $DRY_RUN; then
    echo "DRY RUN. Run with: $0 --apply <efs-filesystem-id>"
else
    echo "Backup is active. First backup will run at next 3am UTC."
    echo "Monitor: aws backup list-backup-jobs --by-backup-vault-name $VAULT_NAME --region $AWS_REGION"
fi
echo "=================================================="
