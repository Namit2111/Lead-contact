from core.interfaces.oauth_provider import OAuthProvider
from providers.gmail.gmail_oauth_provider import GmailOAuthProvider
from core.auth.oauth_service import OAuthService
from core.auth.token_refresher import TokenRefresher
from typing import Dict, Optional


# Provider registry - maps provider names to OAuth provider instances
PROVIDER_REGISTRY: Dict[str, OAuthProvider] = {
    "gmail": GmailOAuthProvider()
}

# Service instances - initialized lazily
_oauth_service: Optional[OAuthService] = None
_token_refresher: Optional[TokenRefresher] = None


async def get_oauth_provider(provider_name: str) -> OAuthProvider:
    """Get OAuth provider instance by name"""
    if provider_name not in PROVIDER_REGISTRY:
        raise ValueError(f"Unsupported provider: {provider_name}")
    return PROVIDER_REGISTRY[provider_name]


async def get_oauth_service() -> OAuthService:
    """Get OAuth service instance"""
    global _oauth_service
    if _oauth_service is None:
        _oauth_service = OAuthService()
    return _oauth_service


async def get_token_refresher() -> TokenRefresher:
    """Get token refresher instance"""
    global _token_refresher
    if _token_refresher is None:
        _token_refresher = TokenRefresher()
    return _token_refresher
