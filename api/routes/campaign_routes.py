from fastapi import APIRouter, Header, HTTPException, Query, Depends
from typing import Optional
from core.campaigns.models import (
    SendCampaignRequest,
    PreviewCampaignRequest,
    CampaignPreviewResponse,
    CampaignResultResponse,
    EmailLogsResponse,
    EmailLogItem,
    CampaignStatsResponse
)
from core.campaigns.campaign_service import CampaignService
from db.repository_factory import get_email_log_repository
from api.dependencies.gmail_token import get_valid_gmail_token
from utils.logger import logger


router = APIRouter(prefix="/campaigns")


def get_user_id_from_header(x_user_id: Optional[str] = Header(None)) -> str:
    """Extract user ID from header"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User authentication required. Missing X-User-Id header")
    return x_user_id


@router.post("/preview", response_model=CampaignPreviewResponse)
async def preview_campaign(
    request: PreviewCampaignRequest,
    x_user_id: Optional[str] = Header(None)
):
    """Preview how campaign will look with first contact"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        preview = await CampaignService.preview_campaign(
            user_id=user_id,
            csv_source=request.csv_source,
            template_id=request.template_id
        )
        
        return CampaignPreviewResponse(**preview)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error previewing campaign: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send", response_model=CampaignResultResponse)
async def send_campaign(
    request: SendCampaignRequest,
    x_user_id: Optional[str] = Header(None),
    gmail_token: str = Depends(get_valid_gmail_token)
):
    """Send email campaign to all contacts in CSV"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        results = await CampaignService.send_campaign(
            user_id=user_id,
            csv_source=request.csv_source,
            template_id=request.template_id,
            access_token=gmail_token
        )
        
        message_parts = []
        if results["sent"] > 0:
            message_parts.append(f"Successfully sent {results['sent']} emails")
        if results["failed"] > 0:
            message_parts.append(f"{results['failed']} failed")
        
        return CampaignResultResponse(
            success=results["sent"] > 0,
            campaign_id=results["campaign_id"],
            total=results["total"],
            sent=results["sent"],
            failed=results["failed"],
            message="; ".join(message_parts) if message_parts else "No emails sent",
            errors=results.get("errors", [])
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error sending campaign: {str(e)}")
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

