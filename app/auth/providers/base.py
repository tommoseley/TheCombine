"""OAuth provider base interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode

from app.auth.models import OAuthTokens, OAuthUserInfo


@dataclass
class OAuthConfig:
    """Configuration for an OAuth provider."""
    client_id: str
    client_secret: str
    redirect_uri: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scopes: list[str]


class OAuthProvider(ABC):
    """Base class for OAuth providers."""
    
    def __init__(self, config: OAuthConfig):
        self.config = config
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'google', 'microsoft')."""
        ...
    
    def get_authorization_url(self, state: str) -> str:
        """
        Get the OAuth authorization URL.
        
        Args:
            state: Random state parameter for CSRF protection
            
        Returns:
            Full authorization URL to redirect user to
        """
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "state": state,
        }
        params.update(self._get_extra_auth_params())
        return f"{self.config.authorize_url}?{urlencode(params)}"
    
    def _get_extra_auth_params(self) -> dict:
        """Override to add provider-specific auth params."""
        return {}
    
    @abstractmethod
    async def exchange_code(self, code: str) -> OAuthTokens:
        """
        Exchange authorization code for tokens.
        
        Args:
            code: Authorization code from OAuth callback
            
        Returns:
            OAuthTokens with access_token and optionally id_token
        """
        ...
    
    @abstractmethod
    async def get_user_info(self, tokens: OAuthTokens) -> OAuthUserInfo:
        """
        Get user information from the provider.
        
        Args:
            tokens: OAuth tokens from exchange_code
            
        Returns:
            OAuthUserInfo with user details
        """
        ...
    
    async def _post_token_request(self, code: str) -> dict:
        """
        Make token exchange request.
        
        Args:
            code: Authorization code
            
        Returns:
            JSON response from token endpoint
        """
        import httpx
        
        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "grant_type": "authorization_code",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_url,
                data=data,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            return response.json()
    
    async def _get_userinfo(self, access_token: str) -> dict:
        """
        Fetch user info from provider's userinfo endpoint.
        
        Args:
            access_token: OAuth access token
            
        Returns:
            JSON response from userinfo endpoint
        """
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.config.userinfo_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            return response.json()
