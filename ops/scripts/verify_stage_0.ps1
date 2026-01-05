# Stage 0 Verification Script (Windows PowerShell)
# Validates auth tables migration

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Stage 0: Database Foundation Verification" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if DATABASE_URL is set
if (-not $env:DATABASE_URL) {
    Write-Host "[FAIL] DATABASE_URL not set" -ForegroundColor Red
    Write-Host "       Example: `$env:DATABASE_URL = 'postgresql://user:pass@localhost:5432/combine'" -ForegroundColor Yellow
    exit 1
}

Write-Host "[PASS] DATABASE_URL is set" -ForegroundColor Green
Write-Host ""

# Test database connection
Write-Host "Testing database connection..."
try {
    $result = psql $env:DATABASE_URL -c "SELECT 1" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[PASS] Database connection successful" -ForegroundColor Green
    } else {
        throw "Connection failed"
    }
} catch {
    Write-Host "[FAIL] Cannot connect to database" -ForegroundColor Red
    Write-Host "       Error: $_" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Check if Alembic is installed
Write-Host "Checking Alembic installation..."
try {
    $result = alembic --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[PASS] Alembic is installed" -ForegroundColor Green
    } else {
        throw "Alembic not found"
    }
} catch {
    Write-Host "[FAIL] Alembic not installed" -ForegroundColor Red
    Write-Host "       Install: pip install alembic" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Verify all 6 tables exist
Write-Host "Verifying tables..."
$tables = @(
    "users",
    "user_oauth_identities",
    "link_intent_nonces",
    "user_sessions",
    "personal_access_tokens",
    "auth_audit_log"
)

$allTablesExist = $true
foreach ($table in $tables) {
    try {
        $result = psql $env:DATABASE_URL -c "SELECT 1 FROM $table LIMIT 0" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [PASS] Table: $table" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] Table missing: $table" -ForegroundColor Red
            $allTablesExist = $false
        }
    } catch {
        Write-Host "  [FAIL] Table missing: $table" -ForegroundColor Red
        $allTablesExist = $false
    }
}

if (-not $allTablesExist) {
    exit 1
}
Write-Host ""

# Verify indexes
Write-Host "Verifying indexes..."
$indexes = @(
    "idx_users_email",
    "idx_users_active",
    "idx_oauth_user_id",
    "idx_oauth_provider",
    "idx_link_nonces_expires",
    "idx_link_nonces_user",
    "idx_session_token",
    "idx_session_user_id",
    "idx_session_expires",
    "idx_pat_user",
    "idx_pat_token_id",
    "idx_pat_active",
    "idx_auth_log_user",
    "idx_auth_log_event",
    "idx_auth_log_created"
)

$allIndexesExist = $true
foreach ($index in $indexes) {
    $query = "SELECT 1 FROM pg_indexes WHERE indexname = '$index'"
    $result = psql $env:DATABASE_URL -t -c $query 2>&1
    if ($result -match "1") {
        Write-Host "  [PASS] Index: $index" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Index missing: $index" -ForegroundColor Red
        $allIndexesExist = $false
    }
}

if (-not $allIndexesExist) {
    exit 1
}
Write-Host ""

# Verify unique constraints
Write-Host "Verifying unique constraints..."
$constraints = @(
    @{Table="users"; Constraint="users_email_unique"},
    @{Table="user_oauth_identities"; Constraint="oauth_provider_user_unique"},
    @{Table="user_sessions"; Constraint="user_sessions_session_token_unique"}
)

$allConstraintsExist = $true
foreach ($c in $constraints) {
    $query = "SELECT 1 FROM pg_constraint WHERE conname = '$($c.Constraint)' AND conrelid = '$($c.Table)'::regclass"
    $result = psql $env:DATABASE_URL -t -c $query 2>&1
    if ($result -match "1") {
        Write-Host "  [PASS] Constraint: $($c.Constraint) on $($c.Table)" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Constraint missing: $($c.Constraint) on $($c.Table)" -ForegroundColor Red
        $allConstraintsExist = $false
    }
}

if (-not $allConstraintsExist) {
    exit 1
}
Write-Host ""

# Verify foreign key constraints
Write-Host "Verifying foreign key constraints..."
$fkQuery = "SELECT COUNT(*) FROM pg_constraint WHERE contype = 'f' AND conrelid IN ('user_oauth_identities'::regclass, 'link_intent_nonces'::regclass, 'user_sessions'::regclass, 'personal_access_tokens'::regclass, 'auth_audit_log'::regclass)"
$fkCount = (psql $env:DATABASE_URL -t -c $fkQuery 2>&1).Trim()

if ($fkCount -eq "5") {
    Write-Host "  [PASS] All 5 foreign key constraints present" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Expected 5 foreign keys, found $fkCount" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Verify timezone-aware timestamps
Write-Host "Verifying timezone-aware columns..."
$tzColumns = @(
    @{Table="users"; Column="user_created_at"},
    @{Table="users"; Column="user_updated_at"},
    @{Table="users"; Column="last_login_at"},
    @{Table="user_sessions"; Column="session_created_at"},
    @{Table="user_sessions"; Column="last_activity_at"},
    @{Table="user_sessions"; Column="expires_at"}
)

$allTzCorrect = $true
foreach ($col in $tzColumns) {
    $dataTypeQuery = "SELECT data_type FROM information_schema.columns WHERE table_name = '$($col.Table)' AND column_name = '$($col.Column)'"
    $dataType = (psql $env:DATABASE_URL -t -c $dataTypeQuery 2>&1).Trim()
    
    if ($dataType -eq "timestamp with time zone") {
        Write-Host "  [PASS] $($col.Table).$($col.Column) is timezone-aware" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $($col.Table).$($col.Column) is NOT timezone-aware (found: $dataType)" -ForegroundColor Red
        $allTzCorrect = $false
    }
}

if (-not $allTzCorrect) {
    exit 1
}
Write-Host ""

# Test unique constraint enforcement
Write-Host "Testing unique constraint enforcement..."
$testEmail = "test-unique-$(Get-Date -Format 'yyyyMMddHHmmss')@example.com"

try {
    $null = psql $env:DATABASE_URL -c "INSERT INTO users (email, name, email_verified) VALUES ('$testEmail', 'Test User', false)" 2>&1
    
    # Try to insert duplicate - should fail
    $duplicateResult = psql $env:DATABASE_URL -c "INSERT INTO users (email, name, email_verified) VALUES ('$testEmail', 'Test User 2', false)" 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [PASS] Unique constraint enforced - duplicate email rejected" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Unique constraint NOT enforced - duplicate email allowed" -ForegroundColor Red
        exit 1
    }
    
    # Cleanup test data
    $null = psql $env:DATABASE_URL -c "DELETE FROM users WHERE email = '$testEmail'" 2>&1
} catch {
    Write-Host "  [WARN] Could not test unique constraint (non-critical)" -ForegroundColor Yellow
}
Write-Host ""

# Test rollback capability
Write-Host "Testing migration rollback..."
try {
    Write-Host "  Running: alembic downgrade -1"
    $null = alembic downgrade -1 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [PASS] Downgrade successful" -ForegroundColor Green
    } else {
        throw "Downgrade failed"
    }
    
    # Verify tables were dropped
    $tableCheck = psql $env:DATABASE_URL -c "SELECT 1 FROM users LIMIT 0" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [PASS] Tables dropped correctly" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Tables still exist after downgrade" -ForegroundColor Red
        exit 1
    }
    
    # Upgrade again
    Write-Host "  Running: alembic upgrade head"
    $null = alembic upgrade head 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [PASS] Upgrade successful" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Upgrade failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  [FAIL] Rollback test failed: $_" -ForegroundColor Red
    Write-Host "  [INFO] Running: alembic upgrade head to restore" -ForegroundColor Yellow
    $null = alembic upgrade head 2>&1
    exit 1
}
Write-Host ""

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "SUCCESS: Stage 0 Verification PASSED" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "All checks passed:" -ForegroundColor Green
Write-Host "  - All 6 tables created"
Write-Host "  - All 15 indexes created"
Write-Host "  - All unique constraints enforced"
Write-Host "  - All foreign keys present"
Write-Host "  - All timestamps timezone-aware"
Write-Host "  - Migration rollback works"
Write-Host ""
Write-Host "[READY] Proceed to Stage 1" -ForegroundColor Green