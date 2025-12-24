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
        
        # Microsoft OIDC
        microsoft_client_id = os.getenv('MICROSOFT_CLIENT_ID')
        microsoft_client_secret = os.getenv('MICROSOFT_CLIENT_SECRET')
        if microsoft_client_id and microsoft_client_secret:
            self.oauth.register(
                name='microsoft',
                client_id=microsoft_client_id,
                client_secret=microsoft_client_secret,
                server_metadata_url='https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration',
                client_kwargs={
                    'scope': 'openid email profile',
                    'code_challenge_method': 'S256'  # PKCE
                }
            )
            self.providers['microsoft'] = {
                'name': 'Microsoft',
                'icon': '/static/icons/microsoft.svg'
            }
            logger.info("Registered Microsoft OIDC provider")
        else:
            logger.info("Microsoft OIDC not configured (MICROSOFT_CLIENT_ID or MICROSOFT_CLIENT_SECRET missing)")
        
        if not self.providers:
            logger.warning(
                "No OIDC providers configured! Set at least one of: "
                "GOOGLE_CLIENT_ID/SECRET or MICROSOFT_CLIENT_ID/SECRET"
            )
    
    def get_enabled_providers(self) -> list:
        """
        Get list of enabled providers for login UI.
        
        Returns:
            List of dicts with 'id', 'name', 'icon' keys
        """
        return [
            {
                'id': provider_id,
                'name': config['name'],
                'icon': config['icon']
            }
            for provider_id, config in self.providers.items()
        ]
    
    def get_client(self, provider_id: str):
        """
        Get Authlib OAuth client for provider.
        
        Args:
            provider_id: Provider identifier ('google', 'microsoft')
            
        Returns:
            Authlib OAuth client instance
            
        Raises:
            ValueError: If provider not configured
        """
        if provider_id not in self.providers:
            raise ValueError(f"Provider '{provider_id}' not configured")
        return self.oauth.create_client(provider_id)
    
    async def parse_id_token(
        self,
        provider_id: str,
        request: Request,
        token: dict
    ) -> Dict[str, Any]:
        """
        Parse and validate ID token using Authlib's OIDC support.
        
        CRITICAL: Must pass request for nonce validation.
        Authlib verifies: signature, issuer, audience, nonce, expiration.
        
        Args:
            provider_id: Provider identifier
            request: Starlette Request (needed for nonce from session)
            token: Token response from OAuth provider
            
        Returns:
            Dict of validated ID token claims
            
        Raises:
            Various Authlib exceptions if validation fails
        """
        client = self.get_client(provider_id)
        claims = await client.parse_id_token(request, token)
        return dict(claims)
    
    def normalize_claims(self, provider_id: str, claims: dict) -> dict:
        """
        Normalize provider-specific claims to standard format.
        
        Handles provider differences:
        - Microsoft may use 'preferred_username' or 'upn' instead of 'email'
        - Google always provides 'email'
        
        Args:
            provider_id: Provider identifier
            claims: Raw claims from ID token
            
        Returns:
            Normalized claims dict with keys: sub, name, email, email_verified, picture
            
        Raises:
            ValueError: If Microsoft token lacks email-like identifier
        """
        normalized = {
            'sub': claims['sub'],
            'name': claims.get('name', ''),
            'email': None,
            'email_verified': False,
            'picture': claims.get('picture')
        }
        
        if provider_id == 'microsoft':
            # Priority 1: Use 'email' claim if present
            email = claims.get('email')
            if email:
                normalized['email'] = email
                normalized['email_verified'] = claims.get('email_verified', False)
                return normalized
            
            # Priority 2: Use 'preferred_username' if it looks like email
            preferred_username = claims.get('preferred_username')
            if preferred_username and '@' in preferred_username:
                normalized['email'] = preferred_username
                normalized['email_verified'] = False  # Cannot trust as verified
                logger.info(
                    f"Microsoft ID token missing 'email', using preferred_username "
                    f"as identifier (marked unverified)"
                )
                return normalized
            
            # Priority 3: Use 'upn' (User Principal Name) if present
            upn = claims.get('upn')
            if upn and '@' in upn:
                normalized['email'] = upn
                normalized['email_verified'] = False
                logger.info(
                    f"Microsoft ID token missing 'email', using upn "
                    f"as identifier (marked unverified)"
                )
                return normalized
            
            # Priority 4: Block login with explicit error
            logger.error(
                f"Microsoft ID token missing email, preferred_username, and upn. "
                f"Cannot create user account. Claims: {claims}"
            )
            raise ValueError(
                "Microsoft account does not provide email address. "
                "Please configure 'email' optional claim in Azure AD. "
                "See: https://learn.microsoft.com/en-us/entra/identity-platform/optional-claims"
            )
        
        elif provider_id == 'google':
            # Google always provides email
            normalized['email'] = claims.get('email')
            normalized['email_verified'] = claims.get('email_verified', False)
        
        return normalized