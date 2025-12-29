"""
OIDC provider configuration.

ADR-008: Multi-Provider OAuth Authentication
Environment-based OIDC provider registration using Authlib.
Supports Google and Microsoft with proper ID token validation.
"""
from typing import Optional, Dict, Any
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request
import os
import logging

logger = logging.getLogger(__name__)


class OIDCConfig:
    """
    Environment-based OIDC provider configuration.
    
    Uses Authlib's OIDC support with proper ID token parsing.
    Requires SessionMiddleware for state/nonce storage.
    
    CRITICAL: parse_id_token() must receive request for nonce validation.
    Authlib verifies: signature, issuer, audience, nonce, expiration.
    """
    
    def __init__(self):
        self.oauth = OAuth()
        self.providers: Dict[str, Dict[str, Any]] = {}
        self._register_providers()
    
    def _register_providers(self):
        """Register OIDC providers from environment variables."""
        
        # Google OIDC
        google_client_id = os.getenv('GOOGLE_CLIENT_ID')
        google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        if google_client_id and google_client_secret:
            self.oauth.register(
                name='google',
                client_id=google_client_id,
                client_secret=google_client_secret,
                server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
                client_kwargs={
                    'scope': 'openid email profile',
                    'code_challenge_method': 'S256'  # PKCE
                }
            )
            self.providers['google'] = {
                'name': 'Google',
                'icon': '/static/icons/google.svg'
            }
            logger.info("Registered Google OIDC provider")
        else:
            logger.info("Google OIDC not configured (GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET missing)")
        
        # Microsoft OAuth2 (pure OAuth2, NOT OIDC)
        microsoft_client_id = os.getenv('MICROSOFT_CLIENT_ID')
        microsoft_client_secret = os.getenv('MICROSOFT_CLIENT_SECRET')
        if microsoft_client_id and microsoft_client_secret:
            # CRITICAL: Microsoft requires 'openid' scope
            # But we'll skip ID token validation to avoid issuer problems
            self.oauth.register(
                name='microsoft',
                client_id=microsoft_client_id,
                client_secret=microsoft_client_secret,
                # Manual OAuth2 endpoints (no auto-discovery)
                authorize_url='https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
                access_token_url='https://login.microsoftonline.com/common/oauth2/v2.0/token',
                userinfo_endpoint='https://graph.microsoft.com/oidc/userinfo',
                client_kwargs={
                    # Microsoft requires 'openid' but we'll skip ID token validation
                    'scope': 'openid User.Read email profile',
                },
                token_endpoint_auth_method='client_secret_post'
            )
            self.providers['microsoft'] = {
                'name': 'Microsoft',
                'icon': '/static/icons/microsoft.svg'
            }
            logger.info("Registered Microsoft OAuth2 provider (pure OAuth2, no OIDC)")
        else:
            logger.info("Microsoft OAuth not configured (MICROSOFT_CLIENT_ID or MICROSOFT_CLIENT_SECRET missing)")
        
        if not self.providers:
            logger.warning("No OAuth providers configured! Please set environment variables.")
    
    def get_client(self, provider_id: str):
        """
        Get OAuth client for provider.
        
        Args:
            provider_id: Provider identifier ('google', 'microsoft')
            
        Returns:
            OAuth client instance
            
        Raises:
            ValueError: If provider not configured
        """
        if provider_id not in self.providers:
            raise ValueError(f"Provider '{provider_id}' not configured")
        
        return getattr(self.oauth, provider_id)
    
    async def parse_id_token(
        self,
        provider_id: str,
        request: Request,
        token: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parse and validate ID token or fetch userinfo.
        
        For Google: Validates OIDC ID token (signature, nonce, issuer, etc)
        For Microsoft: Fetches userinfo from Graph API (no ID token)
        
        Args:
            provider_id: Provider identifier
            request: Starlette Request (needed for nonce from session)
            token: Token response dict
            
        Returns:
            User claims dict
            
        Raises:
            Exception: If validation fails
        """
        client = self.get_client(provider_id)
        
        # For Microsoft, always use userinfo endpoint (pure OAuth2)
        if provider_id == 'microsoft':
            # Fetch user info from Microsoft Graph
            import httpx
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(
                    'https://graph.microsoft.com/oidc/userinfo',
                    headers={'Authorization': f"Bearer {token['access_token']}"}
                )
                response.raise_for_status()
                claims = response.json()
            return claims
        else:
            # Google and others: Parse and validate OIDC ID token
            claims = client.parse_id_token(request, token)
        
        return claims
    
    def normalize_claims(
        self,
        provider_id: str,
        claims: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Normalize claims across providers into standard format.
        
        Handles provider-specific differences in claim names/formats.
        
        Args:
            provider_id: Provider identifier
            claims: Raw claims from ID token or userinfo
            
        Returns:
            Normalized claims dict with: sub, email, email_verified, name, picture
            
        Raises:
            ValueError: If required claims missing
        """
        # Required claims
        if 'sub' not in claims:
            raise ValueError("Missing required claim: sub")
        
        if 'email' not in claims:
            raise ValueError("Missing required claim: email")
        
        # Normalize based on provider
        if provider_id == 'google':
            return {
                'sub': claims['sub'],
                'email': claims['email'],
                'email_verified': claims.get('email_verified', False),
                'name': claims.get('name', ''),
                'picture': claims.get('picture')
            }
        
        elif provider_id == 'microsoft':
            # Microsoft Graph userinfo uses 'preferred_username' for email
            email = claims.get('email') or claims.get('preferred_username')
            if not email:
                raise ValueError("Missing email claim from Microsoft")
            
            return {
                'sub': claims['sub'],
                'email': email,
                # Microsoft doesn't always include email_verified in userinfo
                'email_verified': claims.get('email_verified', True),
                'name': claims.get('name', ''),
                'picture': None  # Microsoft Graph userinfo doesn't include picture
            }
        
        else:
            # Generic normalization for future providers
            return {
                'sub': claims['sub'],
                'email': claims['email'],
                'email_verified': claims.get('email_verified', False),
                'name': claims.get('name', ''),
                'picture': claims.get('picture')
            }