# Stage 4 Diagnostic Script
# Helps identify what's failing

$ErrorActionPreference = "Continue"

Write-Host "Stage 4 Diagnostics" -ForegroundColor Cyan
Write-Host "===================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Check file exists
Write-Host "1. Checking file exists..." -ForegroundColor Yellow
if (Test-Path "app\auth\routes.py") {
    Write-Host "   [PASS] app\auth\routes.py exists" -ForegroundColor Green
} else {
    Write-Host "   [FAIL] app\auth\routes.py missing" -ForegroundColor Red
}
Write-Host ""

# Test 2: Try basic import
Write-Host "2. Testing basic import..." -ForegroundColor Yellow
$importTest = @"
import sys
sys.path.insert(0, 'app')
try:
    from auth.routes import router
    print('   [PASS] Basic import works')
except Exception as e:
    print(f'   [FAIL] Import error: {e}')
    import traceback
    traceback.print_exc()
"@

$importTest | python 2>&1 | ForEach-Object {
    Write-Host $_
}
Write-Host ""

# Test 3: Check dependencies
Write-Host "3. Checking required dependencies..." -ForegroundColor Yellow
$depsTest = @"
import sys
sys.path.insert(0, 'app')

# Check each import individually
imports_to_check = [
    ('fastapi', 'FastAPI basics'),
    ('sqlalchemy.ext.asyncio', 'SQLAlchemy async'),
    ('auth.oidc_config', 'OIDC config'),
    ('auth.service', 'Auth service'),
    ('auth.models', 'Auth models'),
    ('dependencies', 'Dependencies module'),
    ('database', 'Database module'),
    ('middleware.rate_limit', 'Rate limit middleware')
]

for module, description in imports_to_check:
    try:
        __import__(module)
        print(f'   [PASS] {description} ({module})')
    except Exception as e:
        print(f'   [FAIL] {description} ({module}): {e}')
"@

$depsTest | python 2>&1 | ForEach-Object {
    Write-Host $_
}
Write-Host ""

Write-Host "Diagnostics complete. Check failures above." -ForegroundColor Cyan