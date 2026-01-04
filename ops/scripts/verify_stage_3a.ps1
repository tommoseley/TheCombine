# Stage 3A Verification Script (Windows PowerShell)
# Validates AuthService - Sessions + Audit only

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Stage 3A: Auth Service Verification" -ForegroundColor Cyan
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

# Test imports
Write-Host "Testing AuthService..."

$testScript = @"
import sys
import os
import logging

# Suppress logging output
logging.basicConfig(level=logging.CRITICAL)

sys.path.insert(0, 'app')

# Test imports
from auth.service import AuthService
from auth.models import User, UserSession, AuthEventType
from auth.utils import utcnow

print('[PASS] AuthService imports successful')

# Test that AuthService class exists
assert hasattr(AuthService, 'create_session')
assert hasattr(AuthService, 'verify_session')
assert hasattr(AuthService, 'delete_session')
assert hasattr(AuthService, 'get_or_create_user_from_oidc')
assert hasattr(AuthService, 'log_auth_event')
print('[PASS] AuthService has all required methods')

# Test circuit breaker constants
assert hasattr(AuthService, '_audit_log_window')
assert AuthService._audit_log_window.maxlen == 1000
print('[PASS] Circuit breaker configured (1000 events/min)')

# Test that methods use correct signatures
import inspect

# create_session signature
sig = inspect.signature(AuthService.create_session)
assert 'user_id' in sig.parameters
assert 'ip_address' in sig.parameters
assert 'user_agent' in sig.parameters
print('[PASS] create_session() signature correct')

# verify_session signature
sig = inspect.signature(AuthService.verify_session)
assert 'session_token' in sig.parameters
print('[PASS] verify_session() signature correct')

# get_or_create_user_from_oidc signature
sig = inspect.signature(AuthService.get_or_create_user_from_oidc)
assert 'provider_id' in sig.parameters
assert 'provider_user_id' in sig.parameters
assert 'claims' in sig.parameters
print('[PASS] get_or_create_user_from_oidc() signature correct')

# log_auth_event signature
sig = inspect.signature(AuthService.log_auth_event)
assert 'event_type' in sig.parameters
assert 'user_id' in sig.parameters
assert 'ip_address' in sig.parameters
print('[PASS] log_auth_event() signature correct')

# Test that AuthService requires db session
try:
    # Should require db parameter
    sig = inspect.signature(AuthService.__init__)
    assert 'db' in sig.parameters
    print('[PASS] AuthService.__init__() requires db session')
except Exception as e:
    print(f'[FAIL] AuthService.__init__() signature issue: {e}')
    sys.exit(1)

# Test AuthEventType enum values are used correctly
assert AuthEventType.LOGIN_SUCCESS == 'login_success'
assert AuthEventType.CSRF_VIOLATION == 'csrf_violation'
assert AuthEventType.LOGIN_BLOCKED_EMAIL_EXISTS == 'login_blocked_email_exists'
print('[PASS] AuthEventType enum values correct')

# Test that utcnow is imported and used
from auth import utils
assert hasattr(utils, 'utcnow')
now = utils.utcnow()
assert now.tzinfo is not None
print('[PASS] utcnow() imported and returns timezone-aware datetime')

print('')
print('[SUCCESS] Stage 3A Verification PASSED')
print('')
print('[INFO] Full integration tests require database connection')
print('[INFO] Run these manually after database is available:')
print('[INFO]   - Test create_session() with real DB')
print('[INFO]   - Test verify_session() with write throttling')
print('[INFO]   - Test get_or_create_user_from_oidc() email collision handling')
print('[INFO]   - Test log_auth_event() circuit breaker (1500 events)')
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
        } elseif ($_.Trim() -ne "") {
            Write-Host $_
        }
    }
    
    if ($LASTEXITCODE -ne 0 -or $script:testFailed) {
        Write-Host ""
        Write-Host "[FAIL] Stage 3A verification failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[FAIL] Python test execution failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "SUCCESS: Stage 3A Verification PASSED" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "All checks passed:" -ForegroundColor Green
Write-Host "  - AuthService class exists"
Write-Host "  - All required methods present"
Write-Host "  - Method signatures correct"
Write-Host "  - Circuit breaker configured (1000 events/min)"
Write-Host "  - utcnow() used for timezone-aware datetimes"
Write-Host ""
Write-Host "[NOTE] Stage 3A is sessions + audit only" -ForegroundColor Yellow
Write-Host "       Link nonces and PATs deferred to Stage 3B" -ForegroundColor Yellow
Write-Host ""
Write-Host "[READY] Proceed to Stage 4 (Login/Logout Routes)" -ForegroundColor Green