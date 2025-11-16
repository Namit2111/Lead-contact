from fastapi import APIRouter, HTTPException
from api.dependencies.providers import PROVIDER_REGISTRY
from core.auth.models import ConnectedProvider
from typing import List
from utils.logger import logger

router = APIRouter()


@router.get("/providers", response_model=List[str])
async def list_providers():
    """
    List all available OAuth providers.

    Returns a list of provider names that are configured.
    """
    try:
        providers = list(PROVIDER_REGISTRY.keys())
        return providers
    except Exception as e:
        logger.error(f"Failed to list providers: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# TODO: In Phase 2, add endpoint to list connected providers for authenticated user
# This would require user authentication middleware and database queries
