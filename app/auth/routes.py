"""
Authentication routes.

ADR-008: Multi-Provider OAuth Authentication
FastAPI routes for OAuth login/logout flows.

Stage 4: Login + Logout only (Account linking deferred to later stage)
"""
from fastapi import APIRouter, Request, Depends, HTTPException, Header
from fastapi.responses import RedirectResponse
from typing import Optional
from urllib.parse import urlparse
import os
import httpx
import logging

from app.auth.oidc_config import OIDCConfig
from app.auth.service import AuthService
from app.auth.models import AuthEventType
from app.core.dependencies import get_oidc_config
from app.core.database import get_db
from app.middleware.rate_limit import get_client_ip
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_origin(request: Request) -> bool:
    """
    Validate Origin or Referer header against ALLOWED_ORIGINS.
    
    SECURITY: Required for all cookie-authenticated state-changing operations.
    Prevents CSRF attacks even with CSRF token by adding defense-in-depth.
    
    Args:
        request: FastAPI Request
        
    Returns:
        True if origin is valid or no cookies present
        
    Raises:
        HTTPException 403 if origin invalid when cookies present
    """
    # Get cookies
    has_cookies = bool(request.cookies)
    
    if not has_cookies:
        # No cookies = no CSRF risk, allow request
        return True
    
    # Get Origin or Referer
    origin = request.headers.get('Origin') or request.headers.get('Referer')
    
    if not origin:
        logger.warning(f"Missing Origin/Referer header with cookies present from {get_client_ip(request)}")
        raise HTTPException(
            status_code=403,
            detail="Origin validation required"
        )
    
    # Parse origin
    if origin.startswith('http'):
        parsed = urlparse(origin)
        origin_domain = f"{parsed.scheme}://{parsed.netloc}"
    else:
        origin_domain = origin
    
    # Get allowed origins from environment
    allowed_origins = os.getenv('ALLOWED_ORIGINS', '').split(',')
    allowed_origins = [o.strip() for o in allowed_origins if o.strip()]
    
    if not allowed_origins:
        # Development mode - allow all
        logger.debug("No ALLOWED_ORIGINS set - allowing all (development mode)")
        return True
    
    if origin_domain in allowed_origins:
        return True
    
    logger.warning(
        f"Origin validation failed: {origin_domain} not in ALLOWED_ORIGINS "
        f"from IP {get_client_ip(request)}"
    )
    raise HTTPException(
        status_code=403,
        detail="Invalid origin"
    )


def get_cookie_name(name: str, production: bool = None) -> str:
    """
    Get cookie name with __Host- prefix in production.
    
    Args:
        name: Base cookie name ('session' or 'csrf')
        production: Whether in production (defaults to HTTPS_ONLY env var)
        
    Returns:
        Cookie name with __Host- prefix if production
    """
    if production is None:
        production = os.getenv('HTTPS_ONLY', 'false').lower() == 'true'
    
    if production:
        return f"__Host-{name}"
    return name


# ============================================================================
# LOGIN ROUTES
# ============================================================================

@router.get("/login/{provider_id}")
async def login(
    provider_id: str,
    request: Request,
    oidc_config: OIDCConfig = Depends(get_oidc_config)
):
    """
    Initiate OAuth login flow.
    
    Redirects to OAuth provider (Google/Microsoft) with PKCE.
    State and nonce stored in SessionMiddleware session.
    
    Rate limit: 30/min per IP (enforced by Nginx)
    
    Args:
        provider_id: OAuth provider ('google', 'microsoft')
        request: FastAPI Request
        oidc_config: OIDC configuration
        
    Returns:
        302 redirect to OAuth provider
    """
    try:
        client = oidc_config.get_client(provider_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Get redirect URI
    domain = os.getenv('DOMAIN', 'localhost:8000')
    scheme = 'https' if os.getenv('HTTPS_ONLY', 'false').lower() == 'true' else 'http'
    redirect_uri = f"{scheme}://{domain}/auth/callback/{provider_id}"

    # Redirect to OAuth provider
    # Authlib stores state and nonce in session automatically
    logger.info(f"Login - Session keys before redirect: {list(request.session.keys())}")
    logger.info(f"Login - HTTPS_ONLY env: {os.getenv('HTTPS_ONLY', 'not set')}")
    
    return await client.authorize_redirect(request, redirect_uri, prompt='select_account')


@router.get("/callback/{provider_id}")
async def callback(
    provider_id: str,
    request: Request,
    oidc_config: OIDCConfig = Depends(get_oidc_config),
    db: AsyncSession = Depends(get_db)
):
    """
    # DEBUG: Log session and request info
    logger.info(f"Callback - Session keys: {list(request.session.keys())}")
    logger.info(f"Callback - Cookies: {list(request.cookies.keys())}")
    fwd_proto = request.headers.get("x-forwarded-proto", "NOT SET")
    logger.info(f"Callback - X-Forwarded-Proto: {fwd_proto}")
    logger.info(f"Callback - Scheme: {request.url.scheme}")
    
    OAuth callback - exchange code for tokens and create session.
    
    Rate limit: 30/min per IP (enforced by Nginx)
    
    Flow:
    1. Exchange authorization code for tokens
    2. Validate ID token (signature, nonce, expiration)
    3. Normalize claims (handle provider differences)
    4. Create or get user
    5. Create session
    6. Set cookies
    7. Log audit event
    
    Args:
        provider_id: OAuth provider
        request: FastAPI Request
        oidc_config: OIDC configuration
        db: Database session
        
    Returns:
        302 redirect to home page with session cookies set
    """
    # DEBUG: Log session and request info
    logger.info(f"Callback - Session keys: {list(request.session.keys())}")
    logger.info(f"Callback - Cookies: {list(request.cookies.keys())}")
    fwd_proto = request.headers.get("x-forwarded-proto", "NOT SET")
    logger.info(f"Callback - X-Forwarded-Proto: {fwd_proto}")
    logger.info(f"Callback - Scheme: {request.url.scheme}")
    
    try:
        client = oidc_config.get_client(provider_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Build redirect_uri (must match what was sent in authorize request)
    domain = os.getenv('DOMAIN', 'localhost:8000')
    scheme = 'https' if os.getenv('HTTPS_ONLY', 'false').lower() == 'true' else 'http'
    redirect_uri = f"{scheme}://{domain}/auth/callback/{provider_id}"
    
    # Exchange authorization code for tokens
    try:
        if provider_id == 'microsoft':
            # Microsoft: Manual token exchange to avoid Authlib ID token parsing issues
            code = request.query_params.get('code')
            state = request.query_params.get('state')
            
            # Verify state matches session
            session_key = f'_state_microsoft_{state}'
            session_state = request.session.get(session_key)
            if not session_state:
                logger.error(f'Session key {session_key} not found')
                raise ValueError('CSRF state mismatch - session not found')
            # Exchange code for token manually
            async with httpx.AsyncClient() as http_client:
                token_response = await http_client.post(
                    'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                    data={
                        'client_id': os.getenv('MICROSOFT_CLIENT_ID'),
                        'client_secret': os.getenv('MICROSOFT_CLIENT_SECRET'),
                        'code': code,
                        'redirect_uri': redirect_uri,
                        'grant_type': 'authorization_code',
                    }
                )
                token_response.raise_for_status()
                token = token_response.json()
        else:
            # Google and others: Use Authlib
            token = await client.authorize_access_token(request)
    except Exception as e:
        logger.error(f"OAuth token exchange failed for {provider_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail="OAuth authorization failed"
        )
    # Get claims from userinfo (Authlib already validated the token)
    try:
        claims = token.get('userinfo')
        if not claims:
            # Fallback: try to parse id_token manually
            claims = await oidc_config.parse_id_token(provider_id, request, token)
    except Exception as e:
        logger.error(f"ID token validation failed for {provider_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid ID token"
        )
    
    # Normalize claims (handle provider differences)
    try:
        normalized_claims = oidc_config.normalize_claims(provider_id, claims)
    except ValueError as e:
        logger.error(f"Claims normalization failed for {provider_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    
    # Create auth service
    auth_service = AuthService(db)
    
    # Get or create user
    try:
        user, created = await auth_service.get_or_create_user_from_oidc(
            provider_id=provider_id,
            provider_user_id=normalized_claims['sub'],
            claims=normalized_claims
        )
    except ValueError as e:
        # Email collision - block auto-link
        ip_address = get_client_ip(request)
        await auth_service.log_auth_event(
            event_type=AuthEventType.LOGIN_BLOCKED_EMAIL_EXISTS,
            provider_id=provider_id,
            ip_address=ip_address,
            user_agent=request.headers.get('user-agent'),
            metadata={'email': normalized_claims['email']}
        )
        raise HTTPException(status_code=403, detail=str(e))
    
    # Create session
    ip_address = get_client_ip(request)
    session = await auth_service.create_session(
        user_id=user.user_id,
        ip_address=ip_address,
        user_agent=request.headers.get('user-agent')
    )
    
    # Create redirect response
    redirect = RedirectResponse(url='/', status_code=302)
     
    # Set cookies on the redirect response
    production = os.getenv('HTTPS_ONLY', 'false').lower() == 'true'
    
    # Session cookie
    redirect.set_cookie(
        key=get_cookie_name('session', production),
        value=session.session_token,
        max_age=30 * 24 * 60 * 60,  # 30 days
        path='/',
        secure=production,
        httponly=True,
        samesite='lax'
    )
    
    # CSRF cookie
    redirect.set_cookie(
        key=get_cookie_name('csrf', production),
        value=session.csrf_token,
        max_age=30 * 24 * 60 * 60,  # 30 days
        path='/',
        secure=production,
        httponly=False,
        samesite='lax'
    )

    # Log success
    await auth_service.log_auth_event(
        event_type=AuthEventType.LOGIN_SUCCESS,
        user_id=user.user_id,
        provider_id=provider_id,
        ip_address=ip_address,
        user_agent=request.headers.get('user-agent')
    )
    
    action = "created" if created else "logged in"
    logger.info(f"User {user.user_id} {action} via {provider_id}")
    
    # Return redirect with cookies
    return redirect


# ============================================================================
# LOGOUT ROUTE
# ============================================================================

@router.post("/logout")
async def logout(
    request: Request,
    x_csrf_token: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout - delete session and clear cookies.
    
    SECURITY:
    - POST only (no GET)
    - Requires CSRF token in X-CSRF-Token header
    - Requires Origin/Referer validation
    
    Args:
        request: FastAPI Request
        x_csrf_token: CSRF token from header
        db: Database session
        
    Returns:
        200 OK with cookies cleared
    """
    # Validate origin
    validate_origin(request)
    
    # Get session token from cookie
    production = os.getenv('HTTPS_ONLY', 'false').lower() == 'true'
    session_cookie_name = get_cookie_name('session', production)
    csrf_cookie_name = get_cookie_name('csrf', production)
    
    session_token = request.cookies.get(session_cookie_name)
    csrf_token_from_cookie = request.cookies.get(csrf_cookie_name)
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify CSRF token
    if not x_csrf_token or x_csrf_token != csrf_token_from_cookie:
        logger.warning(
            f"CSRF token mismatch in logout from IP {get_client_ip(request)}"
        )
        
        # Log CSRF violation
        auth_service = AuthService(db)
        await auth_service.log_auth_event(
            event_type=AuthEventType.CSRF_VIOLATION,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get('user-agent'),
            metadata={'endpoint': '/auth/logout'}
        )
        
        raise HTTPException(status_code=403, detail="CSRF validation failed")
    
    # Get user_id from session before deleting (for audit log)
    auth_service = AuthService(db)
    session_result = await auth_service.verify_session(session_token)
    user_id = session_result[0].user_id if session_result else None
    
    # Delete session from database
    await auth_service.delete_session(session_token)
    
    # Create response with cookies cleared
    from fastapi.responses import JSONResponse
    response = JSONResponse(content={"status": "logged_out"})
    
    # Clear cookies (CRITICAL: must match Path used when setting)
    response.delete_cookie(
        key=session_cookie_name,
        path='/',
        secure=production,
        httponly=True,
        samesite='lax'
    )
    
    response.delete_cookie(
        key=csrf_cookie_name,
        path='/',
        secure=production,
        httponly=False,
        samesite='lax'
    )
    
    # Log logout
    await auth_service.log_auth_event(
        event_type=AuthEventType.LOGOUT,
        user_id=user_id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get('user-agent')
    )
    
    logger.info(f"User logged out from IP {get_client_ip(request)}")
    
    return response
