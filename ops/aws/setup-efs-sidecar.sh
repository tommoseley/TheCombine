#!/bin/bash
# The Combine - Set up EFS + Postgres Sidecar for Fargate
# Replaces RDS with a Postgres container + EFS persistence
#
# Usage:
#   ./ops/aws/setup-efs-sidecar.sh          # Dry run (shows what it would do)
#   ./ops/aws/setup-efs-sidecar.sh --apply   # Actually create resources
#
# Prerequisites:
#   - AWS CLI configured with appropriate permissions
#   - jq installed
#
# This script creates:
#   1. EFS filesystem (encrypted, lifecycle-managed)
#   2. Mount targets in ECS subnets
#   3. Access point with postgres UID/GID
#   4. Security group for EFS
#   5. Updates ecsTaskRole for EFS access
#   6. Registers new multi-container task definition

set -euo pipefail

# ============================================================
# Configuration — matches current infrastructure
# ============================================================
AWS_REGION="us-east-1"
VPC_ID="vpc-e806728e"
SUBNETS=("subnet-b2bb9f9f" "subnet-7213804e")  # ECS subnets
ECS_SG="sg-0f56d0abd2aa04e8b"                   # Current ECS security group
TASK_FAMILY="the-combine-task"
ECR_REPO="303985543798.dkr.ecr.us-east-1.amazonaws.com/the-combine"
EXECUTION_ROLE="arn:aws:iam::303985543798:role/ecsTaskExecutionRole"
TASK_ROLE="arn:aws:iam::303985543798:role/ecsTaskRole"
ACCOUNT_ID="303985543798"

# Postgres sidecar config
PG_UID=999    # postgres user UID in official postgres image
PG_GID=999    # postgres group GID

DRY_RUN=true
if [ "${1:-}" = "--apply" ]; then
    DRY_RUN=false
fi

log() { echo "[$(date '+%H:%M:%S')] $*"; }
dry() {
    if $DRY_RUN; then
        log "[DRY RUN] Would run: $*"
        return 0
    fi
    log "Running: $*"
    eval "$@"
}

# ============================================================
# Step 1: Create EFS filesystem
# ============================================================
log "=== Step 1: EFS Filesystem ==="

EFS_CMD='aws efs create-file-system \
    --region $AWS_REGION \
    --encrypted \
    --performance-mode generalPurpose \
    --throughput-mode bursting \
    --tags Key=Name,Value=combine-pgdata Key=Environment,Value=production \
    --query "FileSystemId" --output text'

if $DRY_RUN; then
    log "[DRY RUN] Would create encrypted EFS filesystem"
    EFS_ID="fs-PLACEHOLDER"
else
    EFS_ID=$(eval "$EFS_CMD")
    log "Created EFS filesystem: $EFS_ID"

    # Wait for EFS to become available
    log "Waiting for EFS to become available..."
    aws efs describe-file-systems --file-system-id "$EFS_ID" \
        --query 'FileSystems[0].LifeCycleState' --output text
    sleep 5
fi

# Enable lifecycle management (move to IA after 30 days — saves money)
dry "aws efs put-lifecycle-configuration \
    --file-system-id $EFS_ID \
    --lifecycle-policies TransitionToIA=AFTER_30_DAYS TransitionToPrimaryStorageClass=AFTER_1_ACCESS \
    --region $AWS_REGION"

# ============================================================
# Step 2: Create security group for EFS
# ============================================================
log "=== Step 2: EFS Security Group ==="

if $DRY_RUN; then
    log "[DRY RUN] Would create security group for EFS (NFS port 2049)"
    EFS_SG="sg-PLACEHOLDER"
else
    EFS_SG=$(aws ec2 create-security-group \
        --group-name combine-efs-sg \
        --description "EFS access for The Combine Fargate tasks" \
        --vpc-id "$VPC_ID" \
        --query 'GroupId' --output text \
        --region "$AWS_REGION")
    log "Created EFS security group: $EFS_SG"

    # Allow NFS (2049) from ECS security group
    aws ec2 authorize-security-group-ingress \
        --group-id "$EFS_SG" \
        --protocol tcp \
        --port 2049 \
        --source-group "$ECS_SG" \
        --region "$AWS_REGION"
    log "Authorized NFS ingress from ECS SG"
fi

# ============================================================
# Step 3: Create mount targets in each subnet
# ============================================================
log "=== Step 3: EFS Mount Targets ==="

for SUBNET in "${SUBNETS[@]}"; do
    dry "aws efs create-mount-target \
        --file-system-id $EFS_ID \
        --subnet-id $SUBNET \
        --security-groups $EFS_SG \
        --region $AWS_REGION"
done

if ! $DRY_RUN; then
    log "Waiting for mount targets to become available (60s)..."
    sleep 60
fi

# ============================================================
# Step 4: Create EFS access point for Postgres
# ============================================================
log "=== Step 4: EFS Access Point ==="

if $DRY_RUN; then
    log "[DRY RUN] Would create access point with UID=$PG_UID, GID=$PG_GID, path=/pgdata"
    AP_ID="fsap-PLACEHOLDER"
else
    AP_ID=$(aws efs create-access-point \
        --file-system-id "$EFS_ID" \
        --posix-user "Uid=$PG_UID,Gid=$PG_GID" \
        --root-directory "Path=/pgdata,CreationInfo={OwnerUid=$PG_UID,OwnerGid=$PG_GID,Permissions=0700}" \
        --tags Key=Name,Value=combine-pgdata \
        --query 'AccessPointId' --output text \
        --region "$AWS_REGION")
    log "Created EFS access point: $AP_ID"
fi

# ============================================================
# Step 5: Update ecsTaskRole for EFS access
# ============================================================
log "=== Step 5: IAM Policy for EFS ==="

EFS_POLICY=$(cat <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "EFSAccess",
            "Effect": "Allow",
            "Action": [
                "elasticfilesystem:ClientMount",
                "elasticfilesystem:ClientWrite",
                "elasticfilesystem:DescribeMountTargets"
            ],
            "Resource": "arn:aws:elasticfilesystem:${AWS_REGION}:${ACCOUNT_ID}:file-system/${EFS_ID}",
            "Condition": {
                "StringEquals": {
                    "elasticfilesystem:AccessPointArn": "arn:aws:elasticfilesystem:${AWS_REGION}:${ACCOUNT_ID}:access-point/${AP_ID}"
                }
            }
        }
    ]
}
POLICY
)

if $DRY_RUN; then
    log "[DRY RUN] Would attach EFS policy to ecsTaskRole"
    echo "$EFS_POLICY" | jq .
else
    aws iam put-role-policy \
        --role-name ecsTaskRole \
        --policy-name EFSAccessPolicy \
        --policy-document "$EFS_POLICY" \
        --region "$AWS_REGION"
    log "Attached EFS policy to ecsTaskRole"
fi

# ============================================================
# Step 6: Register new multi-container task definition
# ============================================================
log "=== Step 6: Task Definition ==="

# Get the current image tag from the running task
if $DRY_RUN; then
    IMAGE_TAG="latest"
else
    IMAGE_TAG=$(aws ecs describe-services \
        --cluster the-combine-cluster \
        --services the-combine-service \
        --query 'services[0].taskDefinition' --output text \
        --region "$AWS_REGION" | \
        xargs -I {} aws ecs describe-task-definition \
            --task-definition {} \
            --query 'taskDefinition.containerDefinitions[0].image' \
            --output text --region "$AWS_REGION" | \
        sed 's/.*://')
    log "Current image tag: $IMAGE_TAG"
fi

TASK_DEF=$(cat <<TASKDEF
{
    "family": "${TASK_FAMILY}",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "256",
    "memory": "512",
    "executionRoleArn": "${EXECUTION_ROLE}",
    "taskRoleArn": "${TASK_ROLE}",
    "volumes": [
        {
            "name": "pgdata",
            "efsVolumeConfiguration": {
                "fileSystemId": "${EFS_ID}",
                "transitEncryption": "ENABLED",
                "authorizationConfig": {
                    "accessPointId": "${AP_ID}",
                    "iam": "ENABLED"
                }
            }
        }
    ],
    "containerDefinitions": [
        {
            "name": "postgres",
            "image": "postgres:15-alpine",
            "essential": true,
            "cpu": 64,
            "memory": 128,
            "environment": [
                {"name": "POSTGRES_USER", "value": "combine"},
                {"name": "POSTGRES_PASSWORD", "value": "combine-prod-local"},
                {"name": "POSTGRES_DB", "value": "combine"},
                {"name": "PGDATA", "value": "/var/lib/postgresql/data/pgdata"}
            ],
            "mountPoints": [
                {
                    "sourceVolume": "pgdata",
                    "containerPath": "/var/lib/postgresql/data/pgdata"
                }
            ],
            "healthCheck": {
                "command": ["CMD-SHELL", "pg_isready -U combine -d combine"],
                "interval": 10,
                "timeout": 5,
                "retries": 5,
                "startPeriod": 30
            },
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/the-combine",
                    "awslogs-region": "${AWS_REGION}",
                    "awslogs-stream-prefix": "postgres"
                }
            }
        },
        {
            "name": "the-combine",
            "image": "${ECR_REPO}:${IMAGE_TAG}",
            "essential": true,
            "cpu": 192,
            "memory": 384,
            "portMappings": [
                {
                    "containerPort": 8000,
                    "protocol": "tcp"
                }
            ],
            "environment": [
                {"name": "ENVIRONMENT", "value": "production"},
                {"name": "DOMAIN", "value": "www.thecombine.ai"},
                {"name": "HTTPS_ONLY", "value": "true"},
                {"name": "ADMIN_EMAILS", "value": "tommoseley@outlook.com"},
                {"name": "USE_WORKFLOW_ENGINE_LLM", "value": "true"},
                {"name": "DB_HOST", "value": "localhost"},
                {"name": "DB_PORT", "value": "5432"},
                {"name": "DB_USER", "value": "combine"},
                {"name": "DATABASE_URL", "value": "postgresql://combine:combine-prod-local@localhost:5432/combine"}
            ],
            "secrets": [
                {
                    "name": "ANTHROPIC_API_KEY",
                    "valueFrom": "arn:aws:secretsmanager:us-east-1:303985543798:secret:the-combine/anthropic-api-key-eHaYY3"
                }
            ],
            "dependsOn": [
                {
                    "containerName": "postgres",
                    "condition": "HEALTHY"
                }
            ],
            "healthCheck": {
                "command": ["CMD", "curl", "-f", "http://localhost:8000/health"],
                "interval": 30,
                "timeout": 10,
                "retries": 3,
                "startPeriod": 30
            },
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/the-combine",
                    "awslogs-region": "${AWS_REGION}",
                    "awslogs-stream-prefix": "app"
                }
            }
        }
    ]
}
TASKDEF
)

if $DRY_RUN; then
    log "[DRY RUN] Would register task definition:"
    echo "$TASK_DEF" | jq .
else
    echo "$TASK_DEF" > /tmp/combine-task-def.json
    TASK_ARN=$(aws ecs register-task-definition \
        --cli-input-json file:///tmp/combine-task-def.json \
        --query 'taskDefinition.taskDefinitionArn' --output text \
        --region "$AWS_REGION")
    log "Registered task definition: $TASK_ARN"
    rm /tmp/combine-task-def.json
fi

# ============================================================
# Summary
# ============================================================
echo ""
echo "=================================================="
echo "Setup Summary"
echo "=================================================="
echo "EFS Filesystem:  $EFS_ID"
echo "EFS Access Point: $AP_ID"
echo "EFS Security Group: $EFS_SG"
echo "Task CPU/Memory: 256 / 512 (unchanged)"
echo ""
echo "Containers:"
echo "  postgres:     15-alpine (64 CPU, 128 MB, EFS-backed)"
echo "  the-combine:  app (192 CPU, 384 MB)"
echo ""
if $DRY_RUN; then
    echo "This was a DRY RUN. Run with --apply to create resources."
    echo ""
    echo "After --apply, you still need to:"
else
    echo "Resources created. Next steps:"
fi
echo "  1. Migrate data from RDS:  ops/aws/migrate-rds-to-sidecar.sh"
echo "  2. Update ECS service:     aws ecs update-service --cluster the-combine-cluster --service the-combine-service --task-definition $TASK_FAMILY"
echo "  3. Set up AWS Backup:      ops/aws/setup-efs-backup.sh"
echo "  4. Verify health:          curl https://www.thecombine.ai/health"
echo "  5. Retire RDS (after validation): ops/aws/retire-rds.sh"
echo "=================================================="
