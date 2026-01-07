"""
Account linking routes.

ADR-008 Stage 6: Account Linking
Routes for linking/unlinking OAuth providers to existing accounts.
"""
from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from typing import Optional
import os
import logging

from app.auth.oidc_config import OIDCConfig
from app.auth.service import AuthService
from app.auth.models import User, AuthEventType
from app.auth.dependencies import require_auth, get_current_user
from app.core.dependencies import get_oidc_config
from app.core.database import get_db
from app.middleware.rate_limit import get_client_ip
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/accounts", tags=["account-linking"])


# ============================================================================
# VIEW LINKED ACCOUNTS
# ============================================================================

@router.get("")
async def get_linked_accounts(
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all OAuth providers linked to current user.
    
    Returns list of linked identities with provider info.
    
    Returns:
        List of linked provider dicts
    """
    auth_service = AuthService(db)
    identities = await auth_service.get_linked_identities(user.user_id)
    
    return {
        "user_id": str(user.user_id),
        "identities": identities,
        "count": len(identities)
    }


# ============================================================================
# LINK NEW PROVIDER
# ============================================================================

@router.get("/link/{provider_id}")
async def initiate_link(
    provider_id: str,
    request: Request,
    user: User = Depends(require_auth),
    oidc_config: OIDCConfig = Depends(get_oidc_config),
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate account linking flow.
    
    REQUIRES AUTHENTICATION - user must be logged in to link accounts.
    
    Creates link intent nonce, then redirects to OAuth provider.
    Link intent nonce is passed via state parameter and verified in callback.
    
    Args:
        provider_id: Provider to link ('google', 'microsoft')
        request: FastAPI Request
        user: Current authenticated user
        oidc_config: OIDC configuration
        db: Database session
        
    Returns:
        302 redirect to OAuth provider
    """
    try:
        client = oidc_config.get_client(provider_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Create link intent nonce
    auth_service = AuthService(db)
    link_nonce = await auth_service.create_link_intent(
        user_id=user.user_id,
        provider_id=provider_id
    )
    
    # Get redirect URI
    domain = os.getenv('DOMAIN', 'localhost:8000')
    scheme = 'https' if os.getenv('HTTPS_ONLY', 'false').lower() == 'true' else 'http'
    redirect_uri = f"{scheme}://{domain}/auth/accounts/callback/{provider_id}"
    
    # Add link_nonce to state (Authlib will store in session)
    # We'll validate this in the callback
    request.session['link_nonce'] = link_nonce
    
    logger.info(f"Initiating link of {provider_id} for user {user.user_id}")
    
    # Redirect to OAuth provider
    return await client.authorize_redirect(request, redirect_uri, prompt='select_account')


@router.get("/callback/{provider_id}")
async def link_callback(
    provider_id: str,
    request: Request,
    oidc_config: OIDCConfig = Depends(get_oidc_config),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth callback for account linking.
    
    Validates link intent nonce, then links OAuth identity to current user.
    
    Security:
    - Verifies link intent nonce (single-use, 15min expiry)
    - Prevents linking identity already linked to another user
    - Validates OAuth token normally (signature, nonce, etc)
    
    Args:
        provider_id: OAuth provider
        request: FastAPI Request
        oidc_config: OIDC configuration
        db: Database session
        
    Returns:
        302 redirect to accounts page with success/error message
    """
    try:
        client = oidc_config.get_client(provider_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Verify link intent nonce
    link_nonce = request.session.get('link_nonce')
    if not link_nonce:
        logger.warning("Missing link_nonce in session during link callback")
        raise HTTPException(
            status_code=400,
            detail="Invalid linking session"
        )
    
    auth_service = AuthService(db)
    intent = await auth_service.verify_link_intent(link_nonce)
    
    if not intent:
        logger.warning(f"Invalid or expired link intent nonce: {link_nonce[:10]}...")
        raise HTTPException(
            status_code=400,
            detail="Link request expired or invalid. Please try again."
        )
    
    intended_user_id, intended_provider = intent
    
    # Verify provider matches
    if intended_provider != provider_id:
        logger.warning(
            f"Provider mismatch in link callback: "
            f"expected {intended_provider}, got {provider_id}"
        )
        raise HTTPException(
            status_code=400,
            detail="Provider mismatch"
        )
    
    # Exchange authorization code for tokens
    try:
        # For Microsoft, manually fetch token to skip ID token validation
        if provider_id == 'microsoft':
            import httpx
            
            # Get authorization code from callback
            code = request.query_params.get('code')
            if not code:
                raise ValueError("Missing authorization code")
            
            # Get redirect URI
            domain = os.getenv('DOMAIN', 'localhost:8000')
            scheme = 'https' if os.getenv('HTTPS_ONLY', 'false').lower() == 'true' else 'http'
            redirect_uri = f"{scheme}://{domain}/auth/accounts/callback/{provider_id}"
            
            # Get code verifier from session (PKCE)
            code_verifier = request.session.get(f'_microsoft_authlib_code_verifier_')
            
            # Exchange code for token (manual POST request)
            async with httpx.AsyncClient() as http_client:
                token_response = await http_client.post(
                    'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                    data={
                        'client_id': os.getenv('MICROSOFT_CLIENT_ID'),
                        'client_secret': os.getenv('MICROSOFT_CLIENT_SECRET'),
                        'code': code,
                        'redirect_uri': redirect_uri,
                        'grant_type': 'authorization_code',
                        'code_verifier': code_verifier
                    }
                )
                token_response.raise_for_status()
                token = token_response.json()
        else:
            # Google and others: use normal Authlib flow with ID token validation
            token = await client.authorize_access_token(request)
    except Exception as e:
        logger.error(f"OAuth token exchange failed during linking: {e}")
        raise HTTPException(
            status_code=400,
            detail="OAuth authorization failed"
        )
    
    # Get claims
    try:
        claims = token.get('userinfo')
        if not claims:
            claims = await oidc_config.parse_id_token(provider_id, request, token)
    except Exception as e:
        logger.error(f"ID token validation failed during linking: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid ID token"
        )
    
    # Normalize claims
    try:
        normalized_claims = oidc_config.normalize_claims(provider_id, claims)
    except ValueError as e:
        logger.error(f"Claims normalization failed during linking: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    
    # Link identity to user
    try:
        linked = await auth_service.link_oauth_identity(
            user_id=intended_user_id,
            provider_id=provider_id,
            provider_user_id=normalized_claims['sub'],
            claims=normalized_claims
        )
        
        if linked:
            # Log success
            ip_address = get_client_ip(request)
            await auth_service.log_auth_event(
                event_type=AuthEventType.ACCOUNT_LINKED,
                user_id=intended_user_id,
                provider_id=provider_id,
                ip_address=ip_address,
                user_agent=request.headers.get('user-agent'),
                metadata={'provider_email': normalized_claims.get('email')}
            )
            
            logger.info(f"Successfully linked {provider_id} to user {intended_user_id}")
            
            # Redirect to accounts page with success message
            return RedirectResponse(
                url='/?linked=success',
                status_code=302
            )
        else:
            # Already linked (idempotent)
            logger.info(f"{provider_id} already linked to user {intended_user_id}")
            return RedirectResponse(
                url='/?linked=already',
                status_code=302
            )
            
    except ValueError as e:
        # Identity linked to different user
        logger.warning(f"Link attempt blocked: {e}")
        
        # Log blocked attempt
        ip_address = get_client_ip(request)
        await auth_service.log_auth_event(
            event_type=AuthEventType.LINK_BLOCKED_IDENTITY_EXISTS,
            user_id=intended_user_id,
            provider_id=provider_id,
            ip_address=ip_address,
            user_agent=request.headers.get('user-agent'),
            metadata={'error': str(e)}
        )
        
        raise HTTPException(status_code=403, detail=str(e))
    finally:
        # Clean up session
        request.session.pop('link_nonce', None)


# ============================================================================
# UNLINK PROVIDER
# ============================================================================

@router.delete("/{provider_id}")
async def unlink_provider(
    provider_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Unlink OAuth provider from account.
    
    SECURITY: Cannot unlink last provider (would lock user out).
    
    Args:
        provider_id: Provider to unlink
        user: Current authenticated user
        db: Database session
        
    Returns:
        Success message
        
    Raises:
        HTTPException 403: If trying to unlink last provider
    """
    auth_service = AuthService(db)
    
    try:
        deleted = await auth_service.unlink_oauth_identity(
            user_id=user.user_id,
            provider_id=provider_id
        )
        
        if deleted:
            # Log unlink
            await auth_service.log_auth_event(
                event_type=AuthEventType.ACCOUNT_UNLINKED,
                user_id=user.user_id,
                provider_id=provider_id
            )
            
            return {
                "status": "unlinked",
                "provider_id": provider_id
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"{provider_id} not linked to your account"
            )
            
    except ValueError as e:
        # Trying to unlink last provider
        raise HTTPException(
            status_code=403,
            detail=str(e)
        )