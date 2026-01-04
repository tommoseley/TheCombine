# Stage 1 Verification Script (Windows PowerShell)
# Validates models and utilities

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Stage 1: Models & Utilities Verification" -ForegroundColor Cyan
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
Write-Host "Testing module imports..."

$testScript = @"
import sys
sys.path.insert(0, 'app')

# Test auth models
from auth.models import User, AuthContext, OIDCProvider, AuthEventType
from auth.utils import utcnow
from auth.rate_limits import RATE_LIMITS, get_policy
from middleware.rate_limit import get_client_ip

print('[PASS] All imports successful')

# Test enums
assert OIDCProvider.GOOGLE == 'google', 'OIDCProvider.GOOGLE should equal google'
assert OIDCProvider.MICROSOFT == 'microsoft', 'OIDCProvider.MICROSOFT should equal microsoft'
print('[PASS] OIDCProvider enum values correct')

assert AuthEventType.LOGIN_SUCCESS == 'login_success'
assert AuthEventType.CSRF_VIOLATION == 'csrf_violation'
assert AuthEventType.PAT_CREATED == 'pat_created'
print('[PASS] AuthEventType enum values correct')

# Test utcnow
now = utcnow()
assert now.tzinfo is not None, 'utcnow() should return timezone-aware datetime'
print('[PASS] utcnow() returns timezone-aware datetime')

# Test rate limits
assert 'auth_login_redirect' in RATE_LIMITS
assert 'auth_callback' in RATE_LIMITS
assert 'auth_link_initiate' in RATE_LIMITS
assert 'pat_creation' in RATE_LIMITS
assert 'pat_auth_failure' in RATE_LIMITS
assert 'pat_auth_failure_per_token' in RATE_LIMITS
assert 'global_unauth' in RATE_LIMITS
print('[PASS] All rate limit policies defined')

# Test rate limit policy
policy = get_policy('auth_login_redirect')
assert policy.requests == 30
assert policy.key_type == 'ip'
print('[PASS] Rate limit policy structure correct')

# Test rate limit policy string representation
policy_str = str(policy)
assert 'requests' in policy_str or '30' in policy_str
print('[PASS] Rate limit policy __str__ works')

# Test User dataclass
from uuid import UUID, uuid4
from datetime import datetime, timezone

user = User(
    user_id=uuid4(),
    email='test@example.com',
    email_verified=True,
    name='Test User',
    avatar_url=None,
    is_active=True,
    user_created_at=datetime.now(timezone.utc),
    user_updated_at=datetime.now(timezone.utc),
    last_login_at=None
)
assert user.email == 'test@example.com'
print('[PASS] User dataclass instantiates correctly')

# Test AuthContext
auth_context = AuthContext(
    user=user,
    session_id=uuid4(),
    token_id=None,
    csrf_token='test-csrf-token'
)
assert auth_context.user_id == user.user_id
assert auth_context.is_session_auth == True
assert auth_context.is_token_auth == False
print('[PASS] AuthContext properties work correctly')

# Test get_client_ip function exists
import os
from unittest.mock import Mock

# Test with TRUST_PROXY=false (default)
os.environ['TRUST_PROXY'] = 'false'
mock_request = Mock()
mock_request.client.host = '5.6.7.8'
mock_request.headers.get = lambda x: '1.2.3.4' if x == 'X-Forwarded-For' else None

ip = get_client_ip(mock_request)
assert ip == '5.6.7.8', 'Should use socket IP when TRUST_PROXY=false'
print('[PASS] get_client_ip() ignores X-Forwarded-For when TRUST_PROXY=false')

# Test with TRUST_PROXY=true
os.environ['TRUST_PROXY'] = 'true'
ip = get_client_ip(mock_request)
assert ip == '1.2.3.4', 'Should use X-Forwarded-For when TRUST_PROXY=true'
print('[PASS] get_client_ip() uses X-Forwarded-For when TRUST_PROXY=true')

print('')
print('[SUCCESS] Stage 1 Verification PASSED')
"@

try {
    $testScript | python 2>&1 | ForEach-Object {
        if ($_ -match "\[PASS\]") {
            Write-Host $_ -ForegroundColor Green
        } elseif ($_ -match "\[FAIL\]") {
            Write-Host $_ -ForegroundColor Red
            $script:testFailed = $true
        } elseif ($_ -match "\[SUCCESS\]") {
            Write-Host $_ -ForegroundColor Green
        } elseif ($_ -match "Traceback" -or $_ -match "Error" -or $_ -match "assert") {
            Write-Host $_ -ForegroundColor Red
            $script:testFailed = $true
        } else {
            Write-Host $_
        }
    }
    
    if ($LASTEXITCODE -ne 0 -or $script:testFailed) {
        Write-Host ""
        Write-Host "[FAIL] Stage 1 verification failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[FAIL] Python test execution failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "SUCCESS: Stage 1 Verification PASSED" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "All checks passed:" -ForegroundColor Green
Write-Host "  - All modules import successfully"
Write-Host "  - OIDCProvider enum correct"
Write-Host "  - AuthEventType enum correct"
Write-Host "  - utcnow() returns timezone-aware datetime"
Write-Host "  - All rate limit policies defined"
Write-Host "  - User dataclass works"
Write-Host "  - AuthContext properties work"
Write-Host "  - get_client_ip() respects TRUST_PROXY"
Write-Host ""
Write-Host "[READY] Proceed to Stage 2" -ForegroundColor Green