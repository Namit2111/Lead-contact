import httpx
from typing import Dict, Any, List
from datetime import datetime, timedelta
from config import settings
from utils.logger import logger


class GmailClient:
    """Low-level Gmail API client for OAuth operations"""

    # Google OAuth endpoints
    AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    # Gmail API scopes
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ]

    def __init__(self):
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = settings.google_redirect_uri

    def get_auth_url(self, state: str = None) -> str:
        """Generate Google OAuth authorization URL"""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.SCOPES),
            "response_type": "code",
            "access_type": "offline",  # Request refresh token
            "prompt": "consent"  # Force consent screen to get refresh token
        }

        if state:
            params["state"] = state

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.AUTH_URL}?{query_string}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access tokens"""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.TOKEN_URL, data=data)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Failed to exchange code: {e}")
                raise

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.TOKEN_URL, data=data)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Failed to refresh token: {e}")
                raise

    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Get user profile information"""
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.USERINFO_URL, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Failed to get user profile: {e}")
                raise
