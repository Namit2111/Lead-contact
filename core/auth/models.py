from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class OAuthCallbackRequest(BaseModel):
    """Request model for OAuth callback"""
    code: str
    state: Optional[str] = None


class OAuthCallbackResponse(BaseModel):
    """Response model for OAuth callback"""
    status: str
    provider: str
    user: dict


class AuthUrlResponse(BaseModel):
    """Response model for auth URL generation"""
    auth_url: str


class ConnectedProvider(BaseModel):
    """Model for connected provider information"""
    provider: str
    connected_at: datetime
    scope: List[str]
