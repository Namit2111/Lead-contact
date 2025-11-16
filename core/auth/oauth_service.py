from core.interfaces.oauth_provider import OAuthProvider
from core.interfaces.repositories import UserRepository, ProviderTokenRepository
from db.repository_factory import get_user_repository, get_provider_token_repository
from utils.logger import logger
from typing import Dict, Any


class OAuthService:
    """Core OAuth service handling authentication flows"""

    def __init__(
        self,
        user_repo: UserRepository = None,
        token_repo: ProviderTokenRepository = None
    ):
        self.user_repo = user_repo
        self.token_repo = token_repo
        self._initialized = False

    async def _ensure_repos_initialized(self):
        """Ensure repositories are initialized"""
        if not self._initialized:
            if not self.user_repo:
                self.user_repo = await get_user_repository()
            if not self.token_repo:
                self.token_repo = await get_provider_token_repository()
            self._initialized = True

    async def generate_oauth_url(self, provider: OAuthProvider, state: str = None) -> str:
        """Generate OAuth authorization URL for a provider"""
        try:
            auth_url = provider.get_auth_url(state)
            logger.info(f"Generated OAuth URL for provider")
            return auth_url
        except Exception as e:
            logger.error(f"Failed to generate OAuth URL: {e}")
            raise

    async def handle_oauth_callback(
        self,
        provider: OAuthProvider,
        provider_name: str,
        code: str
    ) -> Dict[str, Any]:
        """Handle OAuth callback - exchange code, get profile, save user and tokens"""
        await self._ensure_repos_initialized()
        try:
            # Exchange authorization code for tokens
            logger.info(f"Exchanging code for {provider_name} tokens")
            token_response = await provider.exchange_code(code)

            # Get user profile
            logger.info(f"Getting user profile from {provider_name}")
            user_profile = await provider.get_user_profile(token_response.access_token)

            # Create or get user
            logger.info(f"Creating/getting user: {user_profile.email}")
            user = await self.user_repo.create_user(user_profile.email, user_profile.name)

            # Save provider tokens
            logger.info(f"Saving {provider_name} tokens for user: {user.id}")
            saved_tokens = await self.token_repo.save_tokens(
                user_id=user.id,
                provider=provider_name,
                access_token=token_response.access_token,
                refresh_token=token_response.refresh_token,
                expiry=token_response.expiry,
                scope=token_response.scope
            )

            response = {
                "status": "connected",
                "provider": provider_name,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name
                }
            }

            logger.info(f"Successfully connected {provider_name} for user: {user.email}")
            return response

        except Exception as e:
            logger.error(f"Failed to handle OAuth callback for {provider_name}: {e}")
            raise
