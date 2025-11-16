from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class UserProfile:
    """User profile information from OAuth provider"""
    def __init__(self, email: str, name: str, provider_id: str = None):
        self.email = email
        self.name = name
        self.provider_id = provider_id


class TokenResponse:
    """OAuth token exchange response"""
    def __init__(
        self,
        access_token: str,
        refresh_token: str,
        expiry: datetime,
        scope: list,
        token_type: str = "Bearer"
    ):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expiry = expiry
        self.scope = scope
        self.token_type = token_type


class OAuthProvider(ABC):
    """Abstract OAuth provider interface"""

    @abstractmethod
    def get_auth_url(self, state: str = None) -> str:
        """Generate OAuth authorization URL"""
        pass

    @abstractmethod
    async def exchange_code(self, code: str) -> TokenResponse:
        """Exchange authorization code for access tokens"""
        pass

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token"""
        pass

    @abstractmethod
    async def get_user_profile(self, access_token: str) -> UserProfile:
        """Get user profile information using access token"""
        pass
