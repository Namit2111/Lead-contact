"""
Internal API routes
These endpoints are called by Trigger.dev tasks (not by frontend)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from db.repository_factory import get_email_log_repository
from utils.logger import logger


router = APIRouter(prefix="/internal")


class CreateEmailLogRequest(BaseModel):
    """Request to create email log (from Trigger.dev)"""
    campaign_id: str
    user_id: str
    contact_id: str
    template_id: str
    to_email: str
    subject: str
    body: str
    status: str
    error_message: Optional[str] = None
    sent_at: Optional[str] = None


@router.post("/email-logs")
async def create_email_log(request: CreateEmailLogRequest):
    """
    Create email log entry
    Called by Trigger.dev after sending each email
    """
    try:
        log_repo = await get_email_log_repository()
        
        # Parse sent_at if provided
        sent_at = None
        if request.sent_at:
            try:
                sent_at = datetime.fromisoformat(request.sent_at.replace('Z', '+00:00'))
            except:
                sent_at = datetime.utcnow() if request.status == "sent" else None
        
        # Create log
        log = await log_repo.create_log(
            user_id=request.user_id,
            campaign_id=request.campaign_id,
            contact_id=request.contact_id,
            template_id=request.template_id,
            to_email=request.to_email,
            subject=request.subject,
            body=request.body,
            status=request.status,
            error_message=request.error_message,
            sent_at=sent_at
        )
        
        return {
            "success": True,
            "log_id": log.id
        }
        
    except Exception as e:
        logger.error(f"Error creating email log: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

