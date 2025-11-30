from fastapi import APIRouter, Header, HTTPException, Query, Depends
from typing import Optional
from core.campaigns.models import (
    CreateCampaignRequest,
    PreviewCampaignRequest,
    CampaignPreviewResponse,
    CampaignResultResponse,
    CampaignsListResponse,
    CampaignDetailResponse,
    CampaignItem,
    EmailLogsResponse,
    EmailLogItem,
    CampaignStatsResponse
)
from datetime import datetime
from db.repository_factory import get_email_log_repository, get_campaign_repository, get_contact_repository, get_template_repository
from api.dependencies.gmail_token import get_valid_gmail_token
from integrations.trigger_client import trigger_client
from utils.logger import logger


router = APIRouter(prefix="/campaigns")


def get_user_id_from_header(x_user_id: Optional[str] = Header(None)) -> str:
    """Extract user ID from header"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User authentication required. Missing X-User-Id header")
    return x_user_id


@router.post("/send", response_model=CampaignResultResponse)
async def send_campaign(
    request: CreateCampaignRequest,
    x_user_id: Optional[str] = Header(None),
    gmail_token: str = Depends(get_valid_gmail_token)
):
    """Send email campaign via Trigger.dev (async background job)"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        # Get repositories
        campaign_repo = await get_campaign_repository()
        contact_repo = await get_contact_repository()
        template_repo = await get_template_repository()
        
        # Validate template exists and belongs to user
        template = await template_repo.get_by_id(request.template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        if template.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied to template")
        
        # Get contacts count
        contacts = await contact_repo.get_contacts_by_source(
            user_id, request.csv_source, skip=0, limit=10000
        )
        
        if not contacts:
            raise HTTPException(status_code=404, detail=f"No contacts found in {request.csv_source}")
        
        total_contacts = len(contacts)
        
        # Auto-generate campaign name if not provided
        campaign_name = request.name or f"Campaign - {template.name} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        
        # Validate prompt if provided
        if request.prompt_id:
            from db.repository_factory import get_prompt_repository
            prompt_repo = await get_prompt_repository()
            prompt = await prompt_repo.get_by_id(request.prompt_id)
            if not prompt:
                raise HTTPException(status_code=404, detail="Prompt not found")
            if prompt.user_id != user_id:
                raise HTTPException(status_code=403, detail="Access denied to prompt")
        
        # Create campaign record
        campaign = await campaign_repo.create_campaign(
            user_id=user_id,
            name=campaign_name,
            csv_source=request.csv_source,
            template_id=request.template_id,
            prompt_id=request.prompt_id,
            total_contacts=total_contacts,
            status="queued"
        )
        
        # Get provider token for refresh capability
        from db.repository_factory import get_provider_token_repository
        token_repo = await get_provider_token_repository()
        provider_token = await token_repo.get_by_user_and_provider(user_id, "google")
        
        # Trigger background job
        try:
            trigger_response = await trigger_client.trigger_campaign(
                campaign_id=campaign.id,
                user_id=user_id,
                csv_source=request.csv_source,
                template_id=request.template_id,
                access_token=gmail_token,
                refresh_token=provider_token.refresh_token if provider_token else None,
                token_expiry=provider_token.expiry.isoformat() if provider_token else None
            )
            
            # Store trigger run ID
            if trigger_response.get('id'):
                await campaign_repo.set_trigger_run_id(
                    campaign_id=campaign.id,
                    trigger_run_id=trigger_response['id']
                )
            
        except Exception as e:
            # If trigger fails, mark campaign as failed
            await campaign_repo.update_status(
                campaign_id=campaign.id,
                status="failed",
                error_message=f"Failed to queue job: {str(e)}"
            )
            raise HTTPException(status_code=500, detail=f"Failed to queue campaign: {str(e)}")
        
        return CampaignResultResponse(
            success=True,
            campaign_id=campaign.id,
            total=total_contacts,
            message=f"Campaign '{campaign_name}' queued successfully. Emails will be sent in the background.",
            status="queued"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating campaign: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=CampaignsListResponse)
async def list_campaigns(
    x_user_id: Optional[str] = Header(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None)
):
    """List all campaigns for user"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        campaign_repo = await get_campaign_repository()
        
        skip = (page - 1) * page_size
        
        if status:
            campaigns = await campaign_repo.get_by_status(
                user_id, status, skip=skip, limit=page_size
            )
        else:
            campaigns = await campaign_repo.get_by_user(
                user_id, skip=skip, limit=page_size
            )
        
        total = await campaign_repo.count_by_user(user_id)
        
        campaign_items = [
            CampaignItem(
                id=c.id,
                name=c.name,
                csv_source=c.csv_source,
                template_id=c.template_id,
                prompt_id=c.prompt_id,
                status=c.status,
                total_contacts=c.total_contacts,
                processed=c.processed,
                sent=c.sent,
                failed=c.failed,
                trigger_run_id=c.trigger_run_id,
                error_message=c.error_message,
                auto_reply_enabled=c.auto_reply_enabled,
                auto_reply_subject=c.auto_reply_subject,
                auto_reply_body=c.auto_reply_body,
                max_replies_per_thread=c.max_replies_per_thread,
                replies_count=c.replies_count,
                created_at=c.created_at,
                started_at=c.started_at,
                completed_at=c.completed_at,
                updated_at=c.updated_at
            )
            for c in campaigns
        ]
        
        return CampaignsListResponse(
            campaigns=campaign_items,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing campaigns: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs", response_model=EmailLogsResponse)
async def get_all_email_logs(
    x_user_id: Optional[str] = Header(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None)
):
    """Get all email logs for the user across all campaigns"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        log_repo = await get_email_log_repository()
        
        skip = (page - 1) * page_size
        
        if status:
            logs = await log_repo.get_by_user_and_status(
                user_id, status, skip=skip, limit=page_size
            )
            total = await log_repo.count_by_user_and_status(user_id, status)
        else:
            logs = await log_repo.get_by_user(
                user_id, skip=skip, limit=page_size
            )
            total = await log_repo.count_by_user(user_id)
        
        log_items = [
            EmailLogItem(
                id=log.id,
                campaign_id=log.campaign_id,
                to_email=log.to_email,
                subject=log.subject,
                status=log.status,
                error_message=log.error_message,
                sent_at=log.sent_at,
                created_at=log.created_at
            )
            for log in logs
        ]
        
        return EmailLogsResponse(
            logs=log_items,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error getting email logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{campaign_id}", response_model=CampaignDetailResponse)
async def get_campaign(
    campaign_id: str,
    x_user_id: Optional[str] = Header(None)
):
    """Get campaign details"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        campaign_repo = await get_campaign_repository()
        campaign = await campaign_repo.get_by_id(campaign_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if campaign.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied to campaign")
        
        campaign_item = CampaignItem(
            id=campaign.id,
            name=campaign.name,
            csv_source=campaign.csv_source,
            template_id=campaign.template_id,
            prompt_id=campaign.prompt_id,
            status=campaign.status,
            total_contacts=campaign.total_contacts,
            processed=campaign.processed,
            sent=campaign.sent,
            failed=campaign.failed,
            trigger_run_id=campaign.trigger_run_id,
            error_message=campaign.error_message,
            auto_reply_enabled=campaign.auto_reply_enabled,
            auto_reply_subject=campaign.auto_reply_subject,
            auto_reply_body=campaign.auto_reply_body,
            max_replies_per_thread=campaign.max_replies_per_thread,
            replies_count=campaign.replies_count,
            created_at=campaign.created_at,
            started_at=campaign.started_at,
            completed_at=campaign.completed_at,
            updated_at=campaign.updated_at
        )
        
        return CampaignDetailResponse(campaign=campaign_item)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview", response_model=CampaignPreviewResponse)
async def preview_campaign(
    request: PreviewCampaignRequest,
    x_user_id: Optional[str] = Header(None)
):
    """Preview how campaign will look with first contact"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        # Get repositories
        contact_repo = await get_contact_repository()
        template_repo = await get_template_repository()
        
        # Get template
        template = await template_repo.get_by_id(request.template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        if template.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied to template")
        
        # Get first contact from CSV source
        contacts = await contact_repo.get_contacts_by_source(
            user_id, request.csv_source, skip=0, limit=1
        )
        
        if not contacts:
            raise HTTPException(status_code=404, detail=f"No contacts found in {request.csv_source}")
        
        contact = contacts[0]
        
        # Prepare contact data
        contact_data = {
            "name": contact.name or "there",
            "email": contact.email,
            "company": contact.company or "",
            "phone": contact.phone or "",
            **contact.custom_fields
        }
        
        # Simple template rendering (replace {{variable}} with values)
        rendered_subject = template.subject
        rendered_body = template.body
        
        for key, value in contact_data.items():
            placeholder = "{{" + key + "}}"
            rendered_subject = rendered_subject.replace(placeholder, str(value))
            rendered_body = rendered_body.replace(placeholder, str(value))
        
        return CampaignPreviewResponse(
            to=contact.email,
            subject=rendered_subject,
            body=rendered_body,
            contact_name=contact.name,
            template_name=template.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing campaign: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs", response_model=EmailLogsResponse)
async def get_email_logs(
    x_user_id: Optional[str] = Header(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """Get email logs for user"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        log_repo = await get_email_log_repository()
        
        # Calculate pagination
        skip = (page - 1) * page_size
        
        # Get logs
        logs = await log_repo.get_by_user(user_id, skip=skip, limit=page_size)
        total = await log_repo.count_by_user(user_id)
        
        # Convert to response models
        log_items = [
            EmailLogItem(
                id=log.id,
                campaign_id=log.campaign_id,
                to_email=log.to_email,
                subject=log.subject,
                status=log.status,
                error_message=log.error_message,
                sent_at=log.sent_at,
                created_at=log.created_at
            )
            for log in logs
        ]
        
        return EmailLogsResponse(
            logs=log_items,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error getting email logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/{campaign_id}", response_model=CampaignStatsResponse)
async def get_campaign_stats(
    campaign_id: str,
    x_user_id: Optional[str] = Header(None)
):
    """Get statistics for a specific campaign"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        log_repo = await get_email_log_repository()
        stats = await log_repo.get_campaign_stats(campaign_id)
        
        return CampaignStatsResponse(
            campaign_id=campaign_id,
            total=stats["total"],
            sent=stats["sent"],
            failed=stats["failed"],
            pending=stats["pending"]
        )
        
    except Exception as e:
        logger.error(f"Error getting campaign stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{campaign_id}/emails", response_model=EmailLogsResponse)
async def get_campaign_emails(
    campaign_id: str,
    x_user_id: Optional[str] = Header(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """Get email logs for a specific campaign"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        # Verify user owns this campaign
        campaign_repo = await get_campaign_repository()
        campaign = await campaign_repo.get_by_id(campaign_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        if campaign.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied to campaign")
        
        log_repo = await get_email_log_repository()
        
        skip = (page - 1) * page_size
        logs = await log_repo.get_by_campaign(campaign_id, skip=skip, limit=page_size)
        total = await log_repo.count_by_campaign(campaign_id)
        
        log_items = [
            EmailLogItem(
                id=log.id,
                campaign_id=log.campaign_id,
                to_email=log.to_email,
                subject=log.subject,
                status=log.status,
                error_message=log.error_message,
                sent_at=log.sent_at,
                created_at=log.created_at
            )
            for log in logs
        ]
        
        return EmailLogsResponse(
            logs=log_items,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign emails: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== AUTO-REPLY ENDPOINTS ==============

from pydantic import BaseModel
from db.repository_factory import get_conversation_repository


class UpdateAutoReplyRequest(BaseModel):
    """Request to update auto-reply settings"""
    enabled: bool
    subject: Optional[str] = None
    body: Optional[str] = None
    max_replies: Optional[int] = None
    prompt_id: Optional[str] = None  # AI prompt ID (null to keep current, empty string to clear)


class AutoReplySettingsResponse(BaseModel):
    """Response with auto-reply settings"""
    auto_reply_enabled: bool
    prompt_id: Optional[str] = None
    auto_reply_subject: str
    auto_reply_body: str
    max_replies_per_thread: int
    replies_count: int


@router.get("/{campaign_id}/auto-reply", response_model=AutoReplySettingsResponse)
async def get_auto_reply_settings(
    campaign_id: str,
    x_user_id: Optional[str] = Header(None)
):
    """Get auto-reply settings for a campaign"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        campaign_repo = await get_campaign_repository()
        campaign = await campaign_repo.get_by_id(campaign_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        if campaign.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return AutoReplySettingsResponse(
            auto_reply_enabled=campaign.auto_reply_enabled,
            auto_reply_subject=campaign.auto_reply_subject,
            auto_reply_body=campaign.auto_reply_body,
            max_replies_per_thread=campaign.max_replies_per_thread,
            replies_count=campaign.replies_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting auto-reply settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{campaign_id}/auto-reply", response_model=AutoReplySettingsResponse)
async def update_auto_reply_settings(
    campaign_id: str,
    request: UpdateAutoReplyRequest,
    x_user_id: Optional[str] = Header(None)
):
    """Update auto-reply settings for a campaign"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        campaign_repo = await get_campaign_repository()
        campaign = await campaign_repo.get_by_id(campaign_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        if campaign.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Update settings
        updated = await campaign_repo.update_auto_reply(
            campaign_id=campaign_id,
            enabled=request.enabled,
            subject=request.subject,
            body=request.body,
            max_replies=request.max_replies,
            prompt_id=request.prompt_id
        )
        
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update settings")
        
        return AutoReplySettingsResponse(
            auto_reply_enabled=updated.auto_reply_enabled,
            auto_reply_subject=updated.auto_reply_subject,
            auto_reply_body=updated.auto_reply_body,
            max_replies_per_thread=updated.max_replies_per_thread,
            replies_count=updated.replies_count,
            prompt_id=updated.prompt_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating auto-reply settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class ConversationItem(BaseModel):
    """Single conversation item"""
    id: str
    contact_email: str
    gmail_thread_id: str
    status: str
    message_count: int
    auto_replies_sent: int
    last_message_at: Optional[datetime] = None
    last_reply_at: Optional[datetime] = None
    created_at: datetime


class ConversationsResponse(BaseModel):
    """Response with conversations list"""
    conversations: list[ConversationItem]
    total: int


@router.get("/{campaign_id}/conversations", response_model=ConversationsResponse)
async def get_campaign_conversations(
    campaign_id: str,
    x_user_id: Optional[str] = Header(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """Get conversations for a campaign"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        campaign_repo = await get_campaign_repository()
        campaign = await campaign_repo.get_by_id(campaign_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        if campaign.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        conv_repo = await get_conversation_repository()
        
        skip = (page - 1) * page_size
        conversations = await conv_repo.get_by_campaign(campaign_id, skip=skip, limit=page_size)
        total = await conv_repo.count_by_campaign(campaign_id)
        
        return ConversationsResponse(
            conversations=[
                ConversationItem(
                    id=c.id,
                    contact_email=c.contact_email,
                    gmail_thread_id=c.gmail_thread_id,
                    status=c.status,
                    message_count=c.message_count,
                    auto_replies_sent=c.auto_replies_sent,
                    last_message_at=c.last_message_at,
                    last_reply_at=c.last_reply_at,
                    created_at=c.created_at
                )
                for c in conversations
            ],
            total=total
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class MessageItem(BaseModel):
    """Single message in conversation"""
    id: str
    direction: str
    from_email: str
    to_email: str
    subject: str
    body: str
    is_auto_reply: bool
    sent_at: datetime


class ConversationDetailResponse(BaseModel):
    """Response with conversation details"""
    conversation: ConversationItem
    messages: list[MessageItem]


@router.get("/{campaign_id}/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation_detail(
    campaign_id: str,
    conversation_id: str,
    x_user_id: Optional[str] = Header(None)
):
    """Get conversation with all messages"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        campaign_repo = await get_campaign_repository()
        campaign = await campaign_repo.get_by_id(campaign_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        if campaign.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        conv_repo = await get_conversation_repository()
        
        conversation = await conv_repo.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        messages = await conv_repo.get_messages(conversation_id)
        
        return ConversationDetailResponse(
            conversation=ConversationItem(
                id=conversation.id,
                contact_email=conversation.contact_email,
                gmail_thread_id=conversation.gmail_thread_id,
                status=conversation.status,
                message_count=conversation.message_count,
                auto_replies_sent=conversation.auto_replies_sent,
                last_message_at=conversation.last_message_at,
                last_reply_at=conversation.last_reply_at,
                created_at=conversation.created_at
            ),
            messages=[
                MessageItem(
                    id=m.id,
                    direction=m.direction,
                    from_email=m.from_email,
                    to_email=m.to_email,
                    subject=m.subject,
                    body=m.body,
                    is_auto_reply=m.is_auto_reply,
                    sent_at=m.sent_at
                )
                for m in messages
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

