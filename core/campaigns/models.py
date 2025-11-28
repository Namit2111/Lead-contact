from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class CreateCampaignRequest(BaseModel):
    """Request to create and queue email campaign via Trigger.dev"""
    csv_source: str
    template_id: str
    name: Optional[str] = None  # Auto-generated if not provided


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
    total: int = 0
    sent: int = 0
    failed: int = 0
    message: str
    status: str = "queued"
    errors: List[Dict[str, str]] = []


class CampaignItem(BaseModel):
    """Single campaign item"""
    id: str
    name: str
    csv_source: str
    template_id: str
    status: str
    total_contacts: int
    processed: int
    sent: int
    failed: int
    trigger_run_id: Optional[str] = None
    error_message: Optional[str] = None
    # Auto-reply settings
    auto_reply_enabled: bool = True
    auto_reply_subject: str = "Re: {{original_subject}}"
    auto_reply_body: str = "Thank you for your reply!"
    max_replies_per_thread: int = 3
    replies_count: int = 0
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime


class CampaignsListResponse(BaseModel):
    """Response for campaigns list"""
    campaigns: List[CampaignItem]
    total: int
    page: int
    page_size: int


class CampaignDetailResponse(BaseModel):
    """Response for campaign details"""
    campaign: CampaignItem


class UpdateCampaignStatusRequest(BaseModel):
    """Request to update campaign status"""
    status: str
    error_message: Optional[str] = None


class UpdateCampaignProgressRequest(BaseModel):
    """Request to update campaign progress"""
    processed: int
    sent: int
    failed: int


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

