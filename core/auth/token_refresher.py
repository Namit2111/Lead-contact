from core.interfaces.oauth_provider import OAuthProvider
from core.interfaces.repositories import ProviderTokenRepository
from db.repository_factory import get_provider_token_repository
from datetime import datetime, timedelta
from utils.logger import logger
from typing import Optional


class TokenRefresher:
    """Service for refreshing OAuth tokens when they expire"""

    def __init__(self, token_repo: ProviderTokenRepository = None):
        self.token_repo = token_repo
        # Refresh tokens 5 minutes before expiry to be safe
        self.refresh_buffer_minutes = 5
        self._initialized = False

    async def _ensure_repo_initialized(self):
        """Ensure token repository is initialized"""
        if not self._initialized:
            if not self.token_repo:
                self.token_repo = await get_provider_token_repository()
            self._initialized = True

    async def ensure_valid_token(
        self,
        user_id: str,
        provider: str,
        oauth_provider: OAuthProvider
    ) -> Optional[str]:
        """
        Ensure the user has valid tokens for the provider.
        Returns the access token if valid, None if refresh failed.
        """
        await self._ensure_repo_initialized()
        try:
            # Get current tokens
            tokens = await self.token_repo.get_by_user_and_provider(user_id, provider)
            if not tokens:
                logger.warning(f"No tokens found for user {user_id}, provider {provider}")
                return None

            # Check if token is still valid (with buffer)
            buffer_time = datetime.utcnow() + timedelta(minutes=self.refresh_buffer_minutes)
            if tokens.expiry > buffer_time:
                # Token is still valid
                return tokens.access_token

            # Token needs refresh
            logger.info(f"Refreshing {provider} token for user {user_id}")

            if not tokens.refresh_token:
                logger.error(f"No refresh token available for user {user_id}, provider {provider}")
                return None

            # Refresh the token
            token_response = await oauth_provider.refresh_token(tokens.refresh_token)

            # Update tokens in database
            updated_tokens = await self.token_repo.update_tokens(
                token_id=tokens.id,
                access_token=token_response.access_token,
                refresh_token=token_response.refresh_token,  # May be the same
                expiry=token_response.expiry
            )

            logger.info(f"Successfully refreshed {provider} token for user {user_id}")
            return updated_tokens.access_token

        except Exception as e:
            logger.error(f"Failed to refresh token for user {user_id}, provider {provider}: {e}")
            return None
