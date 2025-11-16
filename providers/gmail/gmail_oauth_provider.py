from core.interfaces.oauth_provider import OAuthProvider, TokenResponse, UserProfile
from .gmail_client import GmailClient
from datetime import datetime, timedelta
from typing import List
from utils.logger import logger


class GmailOAuthProvider(OAuthProvider):
    """Gmail implementation of OAuthProvider interface"""

    def __init__(self):
        self.client = GmailClient()

    def get_auth_url(self, state: str = None) -> str:
        """Generate Gmail OAuth authorization URL"""
        return self.client.get_auth_url(state)

    async def exchange_code(self, code: str) -> TokenResponse:
        """Exchange authorization code for Gmail access tokens"""
        try:
            token_data = await self.client.exchange_code(code)

            # Calculate expiry time
            expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
            expiry = datetime.utcnow() + timedelta(seconds=expires_in)

            # Extract scope
            scope_str = token_data.get("scope", "")
            scope = scope_str.split() if scope_str else []

            return TokenResponse(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token", ""),
                expiry=expiry,
                scope=scope,
                token_type=token_data.get("token_type", "Bearer")
            )
        except Exception as e:
            logger.error(f"Failed to exchange Gmail code: {e}")
            raise

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Refresh Gmail access token"""
        try:
            token_data = await self.client.refresh_access_token(refresh_token)

            # Calculate expiry time
            expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
            expiry = datetime.utcnow() + timedelta(seconds=expires_in)

            # Scope might not be returned on refresh, use default Gmail scopes
            scope = self.client.SCOPES

            return TokenResponse(
                access_token=token_data["access_token"],
                refresh_token=refresh_token,  # Keep the same refresh token
                expiry=expiry,
                scope=scope,
                token_type=token_data.get("token_type", "Bearer")
            )
        except Exception as e:
            logger.error(f"Failed to refresh Gmail token: {e}")
            raise

    async def get_user_profile(self, access_token: str) -> UserProfile:
        """Get Gmail user profile information"""
        try:
            profile_data = await self.client.get_user_profile(access_token)

            return UserProfile(
                email=profile_data["email"],
                name=profile_data.get("name", ""),
                provider_id=profile_data.get("id")
            )
        except Exception as e:
            logger.error(f"Failed to get Gmail user profile: {e}")
            raise
