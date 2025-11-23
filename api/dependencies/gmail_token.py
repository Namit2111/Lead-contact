from fastapi import Header, HTTPException
from datetime import datetime, timedelta
from typing import Optional
from db.repository_factory import get_provider_token_repository
from api.dependencies.providers import get_oauth_provider
from core.auth.token_refresher import TokenRefresher
from utils.logger import logger


async def get_valid_gmail_token(
    x_user_id: Optional[str] = Header(None)
) -> str:
    """
    Dependency that ensures user has valid Gmail token.
    Auto-refreshes if expired.
    
    Args:
        x_user_id: User ID from header
        
    Returns:
        Valid Gmail access token
        
    Raises:
        HTTPException: If user not authenticated or token invalid
    """
    if not x_user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Missing X-User-Id header"
        )
    
    try:
        # Get token repository
        token_repo = await get_provider_token_repository()
        provider_token = await token_repo.get_by_user_and_provider(x_user_id, "google")
        
        if not provider_token:
            raise HTTPException(
                status_code=401,
                detail="Gmail account not connected. Please connect your Gmail account first."
            )
        
        # Check if token is expired or about to expire (5 min buffer)
        buffer_time = datetime.utcnow() + timedelta(minutes=5)
        
        if provider_token.expiry > buffer_time:
            # Token is still valid
            logger.info(f"Using existing valid token for user {x_user_id}")
            return provider_token.access_token
        
        # Token expired or about to expire - refresh it
        logger.info(f"Token expired for user {x_user_id}, refreshing...")
        
        if not provider_token.refresh_token:
            raise HTTPException(
                status_code=401,
                detail="No refresh token available. Please reconnect your Gmail account."
            )
        
        # Get OAuth provider and refresh token
        oauth_provider = await get_oauth_provider("google")
        token_refresher = TokenRefresher(token_repo)
        
        access_token = await token_refresher.ensure_valid_token(
            x_user_id, "google", oauth_provider
        )
        
        if not access_token:
            raise HTTPException(
                status_code=401,
                detail="Failed to refresh Gmail token. Please reconnect your Gmail account."
            )
        
        logger.info(f"Successfully refreshed token for user {x_user_id}")
        return access_token
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token validation failed for user {x_user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Token validation error: {str(e)}"
        )

