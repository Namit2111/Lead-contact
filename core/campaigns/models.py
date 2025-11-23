from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class SendCampaignRequest(BaseModel):
    """Request to send email campaign"""
    csv_source: str
    template_id: str


class PreviewCampaignRequest(BaseModel):
    """Request to preview campaign"""
    csv_source: str
    template_id: str


class CampaignPreviewResponse(BaseModel):
    """Response for campaign preview"""
    to: str
    subject: str
    body: str
    contact_name: Optional[str]
    template_name: str


class CampaignResultResponse(BaseModel):
    """Response for campaign send"""
    success: bool
    campaign_id: str
    total: int
    sent: int
    failed: int
    message: str
    errors: List[Dict[str, str]] = []


class EmailLogItem(BaseModel):
    """Single email log item"""
    id: str
    campaign_id: Optional[str]
    to_email: str
    subject: str
    status: str
    error_message: Optional[str]
    sent_at: Optional[datetime]
    created_at: datetime


class EmailLogsResponse(BaseModel):
    """Response for email logs"""
    logs: List[EmailLogItem]
    total: int
    page: int
    page_size: int


class CampaignStatsResponse(BaseModel):
    """Response for campaign statistics"""
    campaign_id: str
    total: int
    sent: int
    failed: int
    pending: int

