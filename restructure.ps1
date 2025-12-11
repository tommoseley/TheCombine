# Project Restructure Script
# Reorganizes The Combine to clean architecture

$ErrorActionPreference = "Stop"

Write-Host "Restructuring The Combine Project..." -ForegroundColor Cyan
Write-Host ""

# Backup first!
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "backup_$timestamp"

Write-Host "Creating backup: $backupDir" -ForegroundColor Yellow
Copy-Item -Path "app" -Destination $backupDir -Recurse
Write-Host "Backup created" -ForegroundColor Green
Write-Host ""

# Step 1: Rename orchestrator_api to combine
Write-Host "Step 1: Rename orchestrator_api to combine" -ForegroundColor Cyan
if (Test-Path "app\orchestrator_api") {
    Rename-Item "app\orchestrator_api" "app\combine"
    Write-Host "Renamed to app\combine" -ForegroundColor Green
}

# Step 2: Create mentors directory
Write-Host "Step 2: Create mentors directory" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path "app\combine\mentors" | Out-Null

# Move mentor files
if (Test-Path "app\backend\api\pm_test.py") {
    Move-Item "app\backend\api\pm_test.py" "app\combine\mentors\pm_mentor.py"
    Write-Host "Moved pm_test.py to pm_mentor.py" -ForegroundColor Green
}
if (Test-Path "app\backend\api\architect_test.py") {
    Move-Item "app\backend\api\architect_test.py" "app\combine\mentors\architect_mentor.py"
    Write-Host "Moved architect_test.py to architect_mentor.py" -ForegroundColor Green
}
if (Test-Path "app\backend\api\ba_test.py") {
    Move-Item "app\backend\api\ba_test.py" "app\combine\mentors\ba_mentor.py"
    Write-Host "Moved ba_test.py to ba_mentor.py" -ForegroundColor Green
}

# Step 3: Create API directory
Write-Host "Step 3: Create unified api directory" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path "app\api" | Out-Null
New-Item -ItemType Directory -Force -Path "app\api\routers" | Out-Null
New-Item -ItemType Directory -Force -Path "app\api\middleware" | Out-Null

# Copy main.py
if (Test-Path "app\combine\main.py") {
    Copy-Item "app\combine\main.py" "app\api\main.py"
    Write-Host "Copied main.py to api" -ForegroundColor Green
}

# Move routers
if (Test-Path "app\combine\routers") {
    Get-ChildItem "app\combine\routers\*.py" | ForEach-Object {
        Copy-Item $_.FullName "app\api\routers\"
        Write-Host "Copied $($_.Name) to api/routers" -ForegroundColor Green
    }
}

# Copy auth from backend
if (Test-Path "backend\app\routers\auth.py") {
    Copy-Item "backend\app\routers\auth.py" "app\api\routers\auth_backend.py"
    Write-Host "Copied backend auth" -ForegroundColor Green
}

# Copy repo_view
if (Test-Path "experience\app\routers\repo_view.py") {
    Copy-Item "experience\app\routers\repo_view.py" "app\api\routers\"
    Write-Host "Copied repo_view" -ForegroundColor Green
}

# Move middleware
if (Test-Path "app\combine\middleware") {
    Get-ChildItem "app\combine\middleware\*.py" | ForEach-Object {
        Copy-Item $_.FullName "app\api\middleware\"
        Write-Host "Copied $($_.Name) to api/middleware" -ForegroundColor Green
    }
}

# Step 4: Rename experience to web
Write-Host "Step 4: Rename experience to web" -ForegroundColor Cyan
if (Test-Path "experience") {
    Rename-Item "experience" "app\web"
    Write-Host "Renamed to app\web" -ForegroundColor Green
}

# Step 5: Move common models
Write-Host "Step 5: Consolidate models" -ForegroundColor Cyan
if (Test-Path "app\common\models") {
    Get-ChildItem "app\common\models\*.py" | Where-Object { $_.Name -ne "__init__.py" } | ForEach-Object {
        Copy-Item $_.FullName "app\combine\models\pydantic_$($_.Name)"
        Write-Host "Copied $($_.Name) to combine/models" -ForegroundColor Green
    }
}

# Step 6: Reorganize tests
Write-Host "Step 6: Reorganize tests" -ForegroundColor Cyan

# Rename test_orchestrator_api
if (Test-Path "tests\test_orchestrator_api") {
    Rename-Item "tests\test_orchestrator_api" "tests\combine"
    Write-Host "Renamed tests to combine" -ForegroundColor Green
}

# Create api test directory
New-Item -ItemType Directory -Force -Path "tests\api" | Out-Null

# Move backend tests
if (Test-Path "tests\backend") {
    Get-ChildItem "tests\backend\*.py" | ForEach-Object {
        Move-Item $_.FullName "tests\api\"
        Write-Host "Moved $($_.Name) to tests/api" -ForegroundColor Green
    }
    Remove-Item "tests\backend" -Recurse -Force -ErrorAction SilentlyContinue
}

# Rename experience tests
if (Test-Path "tests\experience") {
    Rename-Item "tests\experience" "tests\web"
    Write-Host "Renamed tests\experience to tests\web" -ForegroundColor Green
}

# Summary
Write-Host ""
Write-Host "Restructure Complete!" -ForegroundColor Green
Write-Host ""

Write-Host "New structure:" -ForegroundColor Cyan
Write-Host "app/combine/ - AI engine"
Write-Host "app/api/ - HTTP gateway"
Write-Host "app/web/ - UI"
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Update imports (orchestrator_api to combine)"
Write-Host "2. Delete: workforce, backend, app\common"
Write-Host "3. Run tests"
Write-Host ""

Write-Host "Backup saved in: $backupDir" -ForegroundColor Gray