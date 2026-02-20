# =============================================================================
# WS-AWS-DB-001: Provision RDS Postgres for DEV and TEST
#
# Creates one db.t3.micro RDS instance with two databases (combine_dev,
# combine_test) and separate credentials per database. Security group
# restricts access to the home network IP.
#
# Prerequisites:
#   - AWS CLI configured with appropriate permissions
#   - PowerShell 7+ (pwsh)
#
# Usage:
#   pwsh ops/aws/provision-rds-devtest.ps1
#   pwsh ops/aws/provision-rds-devtest.ps1 -HomeIp "1.2.3.4"
#   pwsh ops/aws/provision-rds-devtest.ps1 -DryRun
#
# To tear down (careful!):
#   pwsh ops/aws/provision-rds-devtest.ps1 -Teardown -ConfirmTeardown "combine-devtest"
# =============================================================================

param(
    [string]$HomeIp = "",
    [switch]$DryRun,
    [switch]$Teardown,
    [string]$ConfirmTeardown = ""
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
$INSTANCE_ID      = "combine-devtest"
$SG_NAME          = "combine-devtest-sg"
$SG_DESC          = "RDS security group for Combine DEV/TEST - home IP only"
$MASTER_USER      = "combine_admin"
$DB_PORT          = 5432
$ENGINE           = "postgres"
$ENGINE_VERSION   = "18.1"
$INSTANCE_CLASS   = "db.t3.micro"
$STORAGE_GB       = 20
$STORAGE_TYPE     = "gp2"
$REGION           = "us-east-1"
$VPC_ID           = "vpc-e806728e"
$SUBNET_GROUP     = "default"

# Database names and their respective users
$DATABASES = @(
    @{ Name = "combine_dev";  User = "combine_dev_user";  SecretName = "the-combine/db-dev" },
    @{ Name = "combine_test"; User = "combine_test_user"; SecretName = "the-combine/db-test" }
)

# ---------------------------------------------------------------------------
# Auto-detect home IP if not provided
# ---------------------------------------------------------------------------
if (-not $HomeIp) {
    Write-Host "Auto-detecting home IP..."
    $HomeIp = (Invoke-RestMethod -Uri "https://checkip.amazonaws.com").Trim()
    Write-Host "  Detected: $HomeIp"
}
$HOME_CIDR = "$HomeIp/32"

# ---------------------------------------------------------------------------
# Teardown path
# ---------------------------------------------------------------------------
if ($Teardown) {
    if ($ConfirmTeardown -ne $INSTANCE_ID) {
        Write-Error "Teardown requires -ConfirmTeardown '$INSTANCE_ID' to prevent accidents."
        exit 1
    }

    Write-Host "=== TEARDOWN: Removing $INSTANCE_ID ==="

    # Delete RDS instance (skip final snapshot for dev/test)
    Write-Host "Deleting RDS instance $INSTANCE_ID..."
    aws rds delete-db-instance `
        --db-instance-identifier $INSTANCE_ID `
        --skip-final-snapshot `
        --region $REGION 2>&1 | Out-Null
    Write-Host "  RDS deletion initiated (may take several minutes)"

    # Wait for deletion
    Write-Host "Waiting for deletion to complete..."
    aws rds wait db-instance-deleted --db-instance-identifier $INSTANCE_ID --region $REGION 2>&1

    # Delete secrets
    foreach ($db in $DATABASES) {
        Write-Host "Deleting secret $($db.SecretName)..."
        aws secretsmanager delete-secret `
            --secret-id $db.SecretName `
            --force-delete-without-recovery `
            --region $REGION 2>&1 | Out-Null
    }
    # Delete master secret
    aws secretsmanager delete-secret `
        --secret-id "the-combine/db-devtest-master" `
        --force-delete-without-recovery `
        --region $REGION 2>&1 | Out-Null

    # Delete security group
    Write-Host "Deleting security group $SG_NAME..."
    $sgId = aws ec2 describe-security-groups `
        --filters "Name=group-name,Values=$SG_NAME" `
        --query 'SecurityGroups[0].GroupId' `
        --output text --region $REGION 2>&1
    if ($sgId -and $sgId -ne "None") {
        aws ec2 delete-security-group --group-id $sgId --region $REGION 2>&1 | Out-Null
    }

    Write-Host "=== TEARDOWN COMPLETE ==="
    exit 0
}

# ---------------------------------------------------------------------------
# Dry run check
# ---------------------------------------------------------------------------
if ($DryRun) {
    Write-Host "=== DRY RUN ==="
    Write-Host "Would create:"
    Write-Host "  Security group: $SG_NAME (allow $HOME_CIDR on port $DB_PORT)"
    Write-Host "  RDS instance:   $INSTANCE_ID ($INSTANCE_CLASS, $ENGINE $ENGINE_VERSION, ${STORAGE_GB}GB)"
    Write-Host "  Databases:      $($DATABASES | ForEach-Object { $_.Name } | Join-String -Separator ', ')"
    Write-Host "  Secrets:        $($DATABASES | ForEach-Object { $_.SecretName } | Join-String -Separator ', ')"
    Write-Host "=== END DRY RUN ==="
    exit 0
}

# ---------------------------------------------------------------------------
# Helper: Generate random password (alphanumeric, 24 chars)
# ---------------------------------------------------------------------------
function New-DbPassword {
    $chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    -join (1..24 | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] })
}

# ---------------------------------------------------------------------------
# Step 1: Create security group
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "=== Step 1: Security Group ==="

# Check if SG already exists
$existingSg = aws ec2 describe-security-groups `
    --filters "Name=group-name,Values=$SG_NAME" `
    --query 'SecurityGroups[0].GroupId' `
    --output text --region $REGION 2>&1

if ($existingSg -and $existingSg -ne "None") {
    Write-Host "  Security group $SG_NAME already exists: $existingSg"
    $SG_ID = $existingSg
} else {
    Write-Host "  Creating security group $SG_NAME..."
    $SG_ID = aws ec2 create-security-group `
        --group-name $SG_NAME `
        --description $SG_DESC `
        --vpc-id $VPC_ID `
        --query 'GroupId' `
        --output text --region $REGION

    Write-Host "  Created: $SG_ID"

    # Add ingress rule: PostgreSQL from home IP only
    aws ec2 authorize-security-group-ingress `
        --group-id $SG_ID `
        --protocol tcp `
        --port $DB_PORT `
        --cidr "$HOME_CIDR" `
        --region $REGION 2>&1 | Out-Null

    Write-Host "  Ingress rule: TCP $DB_PORT from $HOME_CIDR"
}

# ---------------------------------------------------------------------------
# Step 2: Generate master password and store in Secrets Manager
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "=== Step 2: Master Credentials ==="

$MASTER_PASSWORD = New-DbPassword

# Store master credentials
$masterSecret = @{
    host     = "pending-creation"
    port     = $DB_PORT
    username = $MASTER_USER
    password = $MASTER_PASSWORD
    engine   = $ENGINE
} | ConvertTo-Json -Compress

# Check if master secret exists
$existingMaster = aws secretsmanager describe-secret `
    --secret-id "the-combine/db-devtest-master" `
    --region $REGION 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Updating existing master secret..."
    aws secretsmanager put-secret-value `
        --secret-id "the-combine/db-devtest-master" `
        --secret-string $masterSecret `
        --region $REGION 2>&1 | Out-Null
} else {
    Write-Host "  Creating master secret in Secrets Manager..."
    aws secretsmanager create-secret `
        --name "the-combine/db-devtest-master" `
        --description "Master credentials for combine-devtest RDS instance" `
        --secret-string $masterSecret `
        --region $REGION 2>&1 | Out-Null
}
Write-Host "  Master credentials stored: the-combine/db-devtest-master"

# ---------------------------------------------------------------------------
# Step 3: Create RDS instance
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "=== Step 3: RDS Instance ==="

# Check if instance already exists
$existingInstance = aws rds describe-db-instances `
    --db-instance-identifier $INSTANCE_ID `
    --region $REGION 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  RDS instance $INSTANCE_ID already exists"
} else {
    Write-Host "  Creating RDS instance $INSTANCE_ID..."
    Write-Host "  (This will take 5-10 minutes)"

    aws rds create-db-instance `
        --db-instance-identifier $INSTANCE_ID `
        --db-instance-class $INSTANCE_CLASS `
        --engine $ENGINE `
        --engine-version $ENGINE_VERSION `
        --master-username $MASTER_USER `
        --master-user-password $MASTER_PASSWORD `
        --allocated-storage $STORAGE_GB `
        --storage-type $STORAGE_TYPE `
        --vpc-security-group-ids $SG_ID `
        --db-subnet-group-name $SUBNET_GROUP `
        --publicly-accessible `
        --no-multi-az `
        --backup-retention-period 1 `
        --no-deletion-protection `
        --region $REGION 2>&1 | Out-Null

    Write-Host "  Instance creation initiated"
}

# Wait for instance to become available
Write-Host "  Waiting for instance to become available..."
aws rds wait db-instance-available `
    --db-instance-identifier $INSTANCE_ID `
    --region $REGION

# Get the endpoint
$ENDPOINT = aws rds describe-db-instances `
    --db-instance-identifier $INSTANCE_ID `
    --query 'DBInstances[0].Endpoint.Address' `
    --output text --region $REGION

Write-Host "  Endpoint: $ENDPOINT"

# Update master secret with actual endpoint
$masterSecret = @{
    host     = $ENDPOINT
    port     = $DB_PORT
    username = $MASTER_USER
    password = $MASTER_PASSWORD
    engine   = $ENGINE
} | ConvertTo-Json -Compress

aws secretsmanager put-secret-value `
    --secret-id "the-combine/db-devtest-master" `
    --secret-string $masterSecret `
    --region $REGION 2>&1 | Out-Null

# ---------------------------------------------------------------------------
# Step 4: Create databases and users
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "=== Step 4: Databases and Users ==="

# We need psql to create databases and users
if (-not (Get-Command psql -ErrorAction SilentlyContinue)) {
    Write-Host "  WARNING: psql not found. Databases and users must be created manually."
    Write-Host "  Connect with: psql -h $ENDPOINT -U $MASTER_USER -p $DB_PORT postgres"
    Write-Host ""
    Write-Host "  Then run:"
    foreach ($db in $DATABASES) {
        $pw = New-DbPassword
        Write-Host "    CREATE DATABASE $($db.Name);"
        Write-Host "    CREATE USER $($db.User) WITH PASSWORD '$pw';"
        Write-Host "    GRANT ALL PRIVILEGES ON DATABASE $($db.Name) TO $($db.User);"
        Write-Host "    \c $($db.Name)"
        Write-Host "    GRANT ALL ON SCHEMA public TO $($db.User);"
        Write-Host ""
    }
} else {
    $env:PGPASSWORD = $MASTER_PASSWORD

    foreach ($db in $DATABASES) {
        $DB_PASSWORD = New-DbPassword
        Write-Host "  Creating database $($db.Name) and user $($db.User)..."

        # Create database (ignore error if exists)
        psql -h $ENDPOINT -U $MASTER_USER -p $DB_PORT -d postgres `
            -c "CREATE DATABASE $($db.Name);" 2>&1 | Out-Null

        # Create user and grant privileges
        psql -h $ENDPOINT -U $MASTER_USER -p $DB_PORT -d postgres `
            -c "CREATE USER $($db.User) WITH PASSWORD '$DB_PASSWORD';" 2>&1 | Out-Null
        psql -h $ENDPOINT -U $MASTER_USER -p $DB_PORT -d postgres `
            -c "GRANT ALL PRIVILEGES ON DATABASE $($db.Name) TO $($db.User);" 2>&1 | Out-Null
        # Grant schema-level privileges
        psql -h $ENDPOINT -U $MASTER_USER -p $DB_PORT -d $db.Name `
            -c "GRANT ALL ON SCHEMA public TO $($db.User);" 2>&1 | Out-Null

        # Store credentials in Secrets Manager
        $dbSecret = @{
            host         = $ENDPOINT
            port         = $DB_PORT
            username     = $db.User
            password     = $DB_PASSWORD
            dbname       = $db.Name
            engine       = $ENGINE
            DATABASE_URL = "postgresql://$($db.User):${DB_PASSWORD}@${ENDPOINT}:${DB_PORT}/$($db.Name)"
        } | ConvertTo-Json -Compress

        # Check if secret exists
        $existingSecret = aws secretsmanager describe-secret `
            --secret-id $db.SecretName `
            --region $REGION 2>&1
        if ($LASTEXITCODE -eq 0) {
            aws secretsmanager put-secret-value `
                --secret-id $db.SecretName `
                --secret-string $dbSecret `
                --region $REGION 2>&1 | Out-Null
        } else {
            aws secretsmanager create-secret `
                --name $db.SecretName `
                --description "Credentials for $($db.Name) database" `
                --secret-string $dbSecret `
                --region $REGION 2>&1 | Out-Null
        }
        Write-Host "  Credentials stored: $($db.SecretName)"
    }
    $env:PGPASSWORD = ""
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "==========================================="
Write-Host "  PROVISIONING COMPLETE"
Write-Host "==========================================="
Write-Host "  Instance:  $INSTANCE_ID"
Write-Host "  Endpoint:  $ENDPOINT"
Write-Host "  Port:      $DB_PORT"
Write-Host "  SG:        $SG_ID ($HOME_CIDR only)"
Write-Host "  Databases: combine_dev, combine_test"
Write-Host "  Secrets:"
Write-Host "    Master:  the-combine/db-devtest-master"
foreach ($db in $DATABASES) {
    Write-Host "    $($db.Name): $($db.SecretName)"
}
Write-Host "==========================================="
