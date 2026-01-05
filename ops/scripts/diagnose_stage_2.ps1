# Stage 2 Diagnostic Script
# Helps identify what's failing

$ErrorActionPreference = "Continue"

Write-Host "Stage 2 Diagnostics" -ForegroundColor Cyan
Write-Host "===================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Check Authlib installed
Write-Host "1. Checking Authlib installation..." -ForegroundColor Yellow
python -c "import authlib; print(f'   Authlib version: {authlib.__version__}')" 2>&1 | ForEach-Object {
    if ($_ -match "version") {
        Write-Host $_ -ForegroundColor Green
    } else {
        Write-Host "   [FAIL] Authlib not installed" -ForegroundColor Red
        Write-Host "   Run: pip install authlib" -ForegroundColor Yellow
    }
}
Write-Host ""

# Test 2: Check file exists
Write-Host "2. Checking files exist..." -ForegroundColor Yellow
$files = @(
    "app\auth\oidc_config.py",
    "app\dependencies.py"
)
foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "   [PASS] $file" -ForegroundColor Green
    } else {
        Write-Host "   [FAIL] $file missing" -ForegroundColor Red
    }
}
Write-Host ""

# Test 3: Try basic import
Write-Host "3. Testing basic import..." -ForegroundColor Yellow
$importTest = @"
import sys
sys.path.insert(0, 'app')
try:
    from auth.oidc_config import OIDCConfig
    print('   [PASS] OIDCConfig imports')
except Exception as e:
    print(f'   [FAIL] Import error: {e}')
    import traceback
    traceback.print_exc()
"@

$importTest | python 2>&1 | ForEach-Object {
    Write-Host $_
}
Write-Host ""

# Test 4: Check dependencies.py
Write-Host "4. Testing dependencies.py..." -ForegroundColor Yellow
$depsTest = @"
import sys
sys.path.insert(0, 'app')
try:
    from dependencies import get_oidc_config
    print('   [PASS] dependencies imports')
except Exception as e:
    print(f'   [FAIL] Import error: {e}')
    import traceback
    traceback.print_exc()
"@

$depsTest | python 2>&1 | ForEach-Object {
    Write-Host $_
}
Write-Host ""

Write-Host "Diagnostics complete. Fix any [FAIL] items above." -ForegroundColor Cyan