from fastapi import APIRouter, HTTPException, Query
from api.dependencies.providers import get_oauth_provider, get_oauth_service
from core.auth.models import AuthUrlResponse, OAuthCallbackResponse
from utils.logger import logger

router = APIRouter()


@router.get("/auth/{provider}/url", response_model=AuthUrlResponse)
async def get_auth_url(provider: str, state: str = None):
    """
    Generate OAuth authorization URL for the specified provider.

    - **provider**: The OAuth provider (e.g., "gmail")
    - **state**: Optional state parameter for CSRF protection
    """
    try:
        oauth_provider = await get_oauth_provider(provider)
        oauth_service = await get_oauth_service()

        auth_url = await oauth_service.generate_oauth_url(oauth_provider, state)

        return AuthUrlResponse(auth_url=auth_url)

    except ValueError as e:
        logger.warning(f"Invalid provider requested: {provider}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate auth URL for provider {provider}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/auth/{provider}/callback", response_model=OAuthCallbackResponse)
async def oauth_callback(
    provider: str,
    code: str = Query(..., description="Authorization code from OAuth provider"),
    state: str = Query(None, description="State parameter for CSRF protection")
):
    """
    Handle OAuth callback from the provider.

    - **provider**: The OAuth provider (e.g., "gmail")
    - **code**: Authorization code received from the provider
    - **state**: Optional state parameter
    """
    try:
        oauth_provider = await get_oauth_provider(provider)
        oauth_service = await get_oauth_service()

        result = await oauth_service.handle_oauth_callback(
            oauth_provider, provider, code
        )

        return OAuthCallbackResponse(**result)

    except ValueError as e:
        logger.warning(f"Invalid provider in callback: {provider}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"OAuth callback failed for provider {provider}: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")
