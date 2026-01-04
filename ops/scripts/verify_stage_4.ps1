# Stage 4 Verification Script (Windows PowerShell)
# Validates auth routes - Login/Logout only

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Stage 4: Auth Routes Verification" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "app")) {
    Write-Host "[FAIL] app/ directory not found" -ForegroundColor Red
    Write-Host "       Run this script from the project root" -ForegroundColor Yellow
    exit 1
}

Write-Host "[PASS] Project structure validated" -ForegroundColor Green
Write-Host ""

# Test imports and route structure
Write-Host "Testing auth routes..."

$testScript = @"
import sys
import os
import logging

# Suppress logging output
logging.basicConfig(level=logging.CRITICAL)

sys.path.insert(0, 'app')

# Test imports
try:
    from auth.routes import router, validate_origin, get_cookie_name
    from fastapi import APIRouter
    print('[PASS] Auth routes import successful')
except Exception as e:
    print(f'[FAIL] Import failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test router configuration
try:
    assert isinstance(router, APIRouter), 'router should be APIRouter instance'
    assert router.prefix == '/auth', f'router prefix should be /auth, got {router.prefix}'
    print('[PASS] Router configured with /auth prefix')
except AssertionError as e:
    print(f'[FAIL] Router configuration: {e}')
    sys.exit(1)

# Test routes exist by checking router.routes
try:
    route_paths = []
    route_methods = {}
    
    for route in router.routes:
        path = route.path
        route_paths.append(path)
        route_methods[path] = list(route.methods) if hasattr(route, 'methods') else []
    
    # Check paths exist
    assert '/auth/login/{provider_id}' in route_paths, f'Login route missing. Found: {route_paths}'
    assert '/auth/callback/{provider_id}' in route_paths, f'Callback route missing. Found: {route_paths}'
    assert '/auth/logout' in route_paths, f'Logout route missing. Found: {route_paths}'
    print('[PASS] All required routes defined')
    
    # Check methods
    login_methods = route_methods.get('/auth/login/{provider_id}', [])
    assert 'GET' in login_methods, f'Login should be GET, got {login_methods}'
    print('[PASS] Login route is GET')
    
    callback_methods = route_methods.get('/auth/callback/{provider_id}', [])
    assert 'GET' in callback_methods, f'Callback should be GET, got {callback_methods}'
    print('[PASS] Callback route is GET')
    
    logout_methods = route_methods.get('/auth/logout', [])
    assert 'POST' in logout_methods, f'Logout should be POST, got {logout_methods}'
    print('[PASS] Logout route is POST (not GET - CSRF protection)')
    
except AssertionError as e:
    print(f'[FAIL] Route validation: {e}')
    sys.exit(1)
except Exception as e:
    print(f'[FAIL] Route inspection: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test helper functions
try:
    assert callable(validate_origin), 'validate_origin should be callable'
    assert callable(get_cookie_name), 'get_cookie_name should be callable'
    print('[PASS] Helper functions exist')
except AssertionError as e:
    print(f'[FAIL] Helper functions: {e}')
    sys.exit(1)

# Test cookie naming
try:
    cookie_name_dev = get_cookie_name('session', production=False)
    assert cookie_name_dev == 'session', f'Dev cookie should be session, got {cookie_name_dev}'
    print('[PASS] Cookie name in dev mode: session')
    
    cookie_name_prod = get_cookie_name('session', production=True)
    assert cookie_name_prod == '__Host-session', f'Prod cookie should be __Host-session, got {cookie_name_prod}'
    print('[PASS] Cookie name in production: __Host-session')
    
    cookie_name_csrf_dev = get_cookie_name('csrf', production=False)
    assert cookie_name_csrf_dev == 'csrf', f'Dev CSRF cookie should be csrf, got {cookie_name_csrf_dev}'
    print('[PASS] CSRF cookie name in dev mode: csrf')
    
    cookie_name_csrf_prod = get_cookie_name('csrf', production=True)
    assert cookie_name_csrf_prod == '__Host-csrf', f'Prod CSRF cookie should be __Host-csrf, got {cookie_name_csrf_prod}'
    print('[PASS] CSRF cookie name in production: __Host-csrf')
except AssertionError as e:
    print(f'[FAIL] Cookie naming: {e}')
    sys.exit(1)

# Test validate_origin function signature
try:
    import inspect
    sig = inspect.signature(validate_origin)
    assert 'request' in sig.parameters, 'validate_origin should have request parameter'
    print('[PASS] validate_origin has correct signature')
except AssertionError as e:
    print(f'[FAIL] validate_origin signature: {e}')
    sys.exit(1)

print('')
print('[SUCCESS] Stage 4 Verification PASSED')
print('')
print('[INFO] Route structure validated - ready for integration testing')
print('[INFO] Next: Add router to main.py and test with real OAuth providers')
"@

try {
    $output = $testScript | python 2>&1 | Out-String
    
    $output -split "`n" | ForEach-Object {
        if ($_ -match "\[PASS\]") {
            Write-Host $_ -ForegroundColor Green
        } elseif ($_ -match "\[FAIL\]") {
            Write-Host $_ -ForegroundColor Red
            $script:testFailed = $true
        } elseif ($_ -match "\[SUCCESS\]") {
            Write-Host $_ -ForegroundColor Green
        } elseif ($_ -match "\[INFO\]") {
            Write-Host $_ -ForegroundColor Cyan
        } elseif ($_ -match "Traceback") {
            Write-Host $_ -ForegroundColor Red
            $script:testFailed = $true
        } elseif ($_.Trim() -ne "") {
            Write-Host $_
        }
    }
    
    if ($LASTEXITCODE -ne 0 -or $script:testFailed) {
        Write-Host ""
        Write-Host "[FAIL] Stage 4 verification failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[FAIL] Python test execution failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "SUCCESS: Stage 4 Verification PASSED" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "All checks passed:" -ForegroundColor Green
Write-Host "  - Router configured with /auth prefix"
Write-Host "  - All 3 routes defined (login, callback, logout)"
Write-Host "  - Login is GET, Callback is GET, Logout is POST"
Write-Host "  - Cookie names correct (session/__Host-session)"
Write-Host "  - Helper functions exist (validate_origin, get_cookie_name)"
Write-Host ""
Write-Host "[NEXT] Add router to main.py:" -ForegroundColor Yellow
Write-Host "       from auth.routes import router as auth_router" -ForegroundColor Yellow
Write-Host "       app.include_router(auth_router)" -ForegroundColor Yellow
Write-Host ""
Write-Host "[READY] Proceed to Stage 5 (Auth Middleware)" -ForegroundColor Green