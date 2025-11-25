from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from pydantic import BaseModel
from db.repository_factory import get_campaign_repository
from utils.logger import logger


router = APIRouter(prefix="/webhooks/trigger")


class CampaignStatusUpdate(BaseModel):
    """Webhook payload for campaign status update"""
    campaign_id: str
    status: str
    error_message: Optional[str] = None


class CampaignProgressUpdate(BaseModel):
    """Webhook payload for campaign progress update"""
    campaign_id: str
    processed: int
    sent: int
    failed: int


@router.post("/campaign-status")
async def update_campaign_status(
    payload: CampaignStatusUpdate,
    x_webhook_secret: Optional[str] = Header(None)
):
    """
    Webhook endpoint for Trigger.dev to update campaign status
    
    Called when campaign status changes (running, completed, failed, etc.)
    """
    # TODO: Validate webhook secret for security
    # if x_webhook_secret != settings.TRIGGER_WEBHOOK_SECRET:
    #     raise HTTPException(status_code=401, detail="Invalid webhook secret")
    
    try:
        campaign_repo = await get_campaign_repository()
        
        campaign = await campaign_repo.update_status(
            campaign_id=payload.campaign_id,
            status=payload.status,
            error_message=payload.error_message
        )
        
        if not campaign:
            logger.warning(f"Campaign {payload.campaign_id} not found for status update")
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        logger.info(f"Updated campaign {payload.campaign_id} status to {payload.status}")
        
        return {
            "success": True,
            "campaign_id": campaign.id,
            "status": campaign.status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating campaign status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/campaign-progress")
async def update_campaign_progress(
    payload: CampaignProgressUpdate,
    x_webhook_secret: Optional[str] = Header(None)
):
    """
    Webhook endpoint for Trigger.dev to update campaign progress
    
    Called after each email is sent to update progress counters
    """
    # TODO: Validate webhook secret for security
    # if x_webhook_secret != settings.TRIGGER_WEBHOOK_SECRET:
    #     raise HTTPException(status_code=401, detail="Invalid webhook secret")
    
    try:
        campaign_repo = await get_campaign_repository()
        
        campaign = await campaign_repo.update_progress(
            campaign_id=payload.campaign_id,
            processed=payload.processed,
            sent=payload.sent,
            failed=payload.failed
        )
        
        if not campaign:
            logger.warning(f"Campaign {payload.campaign_id} not found for progress update")
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        logger.debug(f"Updated campaign {payload.campaign_id} progress: {payload.sent}/{campaign.total_contacts}")
        
        return {
            "success": True,
            "campaign_id": campaign.id,
            "processed": campaign.processed,
            "sent": campaign.sent,
            "failed": campaign.failed
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating campaign progress: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-run-id")
async def set_trigger_run_id(
    campaign_id: str,
    run_id: str,
    x_webhook_secret: Optional[str] = Header(None)
):
    """
    Webhook endpoint to store Trigger.dev run ID
    
    Called when Trigger.dev job starts
    """
    # TODO: Validate webhook secret for security
    
    try:
        campaign_repo = await get_campaign_repository()
        
        campaign = await campaign_repo.set_trigger_run_id(
            campaign_id=campaign_id,
            trigger_run_id=run_id
        )
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        logger.info(f"Set Trigger.dev run ID {run_id} for campaign {campaign_id}")
        
        return {
            "success": True,
            "campaign_id": campaign.id,
            "trigger_run_id": campaign.trigger_run_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting trigger run ID: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

