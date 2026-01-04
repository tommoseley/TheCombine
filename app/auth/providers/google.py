"""Google OAuth provider."""

from app.auth.models import OAuthTokens, OAuthUserInfo
from .base import OAuthProvider, OAuthConfig


def create_google_config(
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> OAuthConfig:
    """Create Google OAuth configuration."""
    return OAuthConfig(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        userinfo_url="https://www.googleapis.com/oauth2/v3/userinfo",
        scopes=["openid", "email", "profile"],
    )


class GoogleOAuthProvider(OAuthProvider):
    """Google OAuth 2.0 provider."""
    
    @property
    def provider_name(self) -> str:
        return "google"
    
    def _get_extra_auth_params(self) -> dict:
        """Add Google-specific auth params."""
        return {
            "access_type": "offline",  # Get refresh token
            "prompt": "consent",  # Force consent to get refresh token
        }
    
    async def exchange_code(self, code: str) -> OAuthTokens:
        """Exchange authorization code for Google tokens."""
        data = await self._post_token_request(code)
        
        return OAuthTokens(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in"),
            refresh_token=data.get("refresh_token"),
            id_token=data.get("id_token"),
            scope=data.get("scope"),
        )
    
    async def get_user_info(self, tokens: OAuthTokens) -> OAuthUserInfo:
        """Get user info from Google."""
        data = await self._get_userinfo(tokens.access_token)
        
        return OAuthUserInfo(
            provider_id=data["sub"],
            email=data["email"],
            name=data.get("name", data["email"].split("@")[0]),
            picture_url=data.get("picture"),
            email_verified=data.get("email_verified", False),
        )
