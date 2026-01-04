# Stage 2 Verification Script (Windows PowerShell)
# Validates OIDC configuration

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Stage 2: OIDC Configuration Verification" -ForegroundColor Cyan
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

# Test imports and functionality
Write-Host "Testing OIDC configuration..."

$testScript = @"
import sys
import os
import logging

# Suppress logging output for cleaner test results
logging.basicConfig(level=logging.CRITICAL)

sys.path.insert(0, 'app')

# Set test OAuth credentials
os.environ['GOOGLE_CLIENT_ID'] = 'test-google-client-id'
os.environ['GOOGLE_CLIENT_SECRET'] = 'test-google-secret'
os.environ['MICROSOFT_CLIENT_ID'] = 'test-microsoft-client-id'
os.environ['MICROSOFT_CLIENT_SECRET'] = 'test-microsoft-secret'

# Test imports
from auth.oidc_config import OIDCConfig
from dependencies import get_oidc_config

print('[PASS] OIDC imports successful')

# Test OIDCConfig instantiation
config = OIDCConfig()
print('[PASS] OIDCConfig instantiates')

# Test providers registered
assert 'google' in config.providers, 'Google provider should be registered'
assert 'microsoft' in config.providers, 'Microsoft provider should be registered'
print('[PASS] Google and Microsoft providers registered')

# Test get_enabled_providers
providers = config.get_enabled_providers()
assert len(providers) == 2, 'Should have 2 providers'
assert any(p['id'] == 'google' for p in providers)
assert any(p['id'] == 'microsoft' for p in providers)
print('[PASS] get_enabled_providers() works')

# Test get_client
google_client = config.get_client('google')
assert google_client is not None
print('[PASS] get_client() returns client')

# Test get_client with invalid provider
try:
    config.get_client('invalid')
    print('[FAIL] Should raise ValueError for invalid provider')
    sys.exit(1)
except ValueError as e:
    assert 'not configured' in str(e)
    print('[PASS] get_client() raises ValueError for invalid provider')

# Test normalize_claims - Google
google_claims = {
    'sub': '123456',
    'name': 'Test User',
    'email': 'test@gmail.com',
    'email_verified': True,
    'picture': 'https://example.com/photo.jpg'
}
normalized = config.normalize_claims('google', google_claims)
assert normalized['sub'] == '123456'
assert normalized['email'] == 'test@gmail.com'
assert normalized['email_verified'] == True
assert normalized['name'] == 'Test User'
print('[PASS] normalize_claims() works for Google')

# Test normalize_claims - Microsoft with email
microsoft_claims = {
    'sub': '789012',
    'name': 'Test User MS',
    'email': 'test@outlook.com',
    'email_verified': True
}
normalized = config.normalize_claims('microsoft', microsoft_claims)
assert normalized['email'] == 'test@outlook.com'
assert normalized['email_verified'] == True
print('[PASS] normalize_claims() works for Microsoft with email')

# Test normalize_claims - Microsoft with preferred_username fallback
microsoft_claims_no_email = {
    'sub': '789012',
    'name': 'Test User MS',
    'preferred_username': 'test@outlook.com'
}
normalized = config.normalize_claims('microsoft', microsoft_claims_no_email)
assert normalized['email'] == 'test@outlook.com'
assert normalized['email_verified'] == False  # Fallback marked as unverified
print('[PASS] normalize_claims() uses preferred_username fallback for Microsoft')

# Test normalize_claims - Microsoft with upn fallback
microsoft_claims_upn = {
    'sub': '789012',
    'name': 'Test User MS',
    'upn': 'testuser@company.com'
}
normalized = config.normalize_claims('microsoft', microsoft_claims_upn)
assert normalized['email'] == 'testuser@company.com'
assert normalized['email_verified'] == False
print('[PASS] normalize_claims() uses upn fallback for Microsoft')

# Test normalize_claims - Microsoft without email-like claim (should raise ValueError)
microsoft_claims_no_identifier = {
    'sub': '789012',
    'name': 'Test User MS'
}
error_raised = False
try:
    config.normalize_claims('microsoft', microsoft_claims_no_identifier)
except ValueError as e:
    if 'does not provide email address' in str(e):
        error_raised = True
    else:
        print(f'[FAIL] Wrong error message: {e}')
        sys.exit(1)

if error_raised:
    print('[PASS] normalize_claims() raises ValueError when no email identifier')
else:
    print('[FAIL] Should raise ValueError when no email identifier')
    sys.exit(1)

# Test dependency function
oidc_config = get_oidc_config()
assert oidc_config is not None
assert isinstance(oidc_config, OIDCConfig)
print('[PASS] get_oidc_config() dependency works')

# Test singleton pattern (lru_cache)
oidc_config2 = get_oidc_config()
assert oidc_config is oidc_config2, 'Should return same instance (singleton)'
print('[PASS] get_oidc_config() returns singleton instance')

# Test without OAuth credentials
os.environ.pop('GOOGLE_CLIENT_ID', None)
os.environ.pop('GOOGLE_CLIENT_SECRET', None)
os.environ.pop('MICROSOFT_CLIENT_ID', None)
os.environ.pop('MICROSOFT_CLIENT_SECRET', None)

config_no_providers = OIDCConfig()
assert len(config_no_providers.providers) == 0
print('[PASS] OIDCConfig works with no providers configured')

print('')
print('[SUCCESS] Stage 2 Verification PASSED')
"@

try {
    # Run Python script and capture only stdout (suppress stderr where logging goes)
    $output = $testScript | python 2>&1 | Out-String
    
    # Display output
    $output -split "`n" | ForEach-Object {
        if ($_ -match "\[PASS\]") {
            Write-Host $_ -ForegroundColor Green
        } elseif ($_ -match "\[FAIL\]") {
            Write-Host $_ -ForegroundColor Red
            $script:testFailed = $true
        } elseif ($_ -match "\[SUCCESS\]") {
            Write-Host $_ -ForegroundColor Green
        } elseif ($_.Trim() -ne "") {
            Write-Host $_
        }
    }
    
    if ($LASTEXITCODE -ne 0 -or $script:testFailed) {
        Write-Host ""
        Write-Host "[FAIL] Stage 2 verification failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[FAIL] Python test execution failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "SUCCESS: Stage 2 Verification PASSED" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "All checks passed:" -ForegroundColor Green
Write-Host "  - OIDCConfig instantiates"
Write-Host "  - Google and Microsoft providers registered"
Write-Host "  - get_enabled_providers() works"
Write-Host "  - get_client() returns OAuth client"
Write-Host "  - normalize_claims() handles all Microsoft fallbacks"
Write-Host "  - get_oidc_config() dependency works (singleton)"
Write-Host "  - Works with no providers configured"
Write-Host ""
Write-Host "[IMPORTANT] Next step: Add SessionMiddleware to main.py" -ForegroundColor Yellow
Write-Host "            See: main_py_session_middleware.py for code to add" -ForegroundColor Yellow
Write-Host ""
Write-Host "[READY] Proceed to Stage 3 (after adding SessionMiddleware)" -ForegroundColor Green