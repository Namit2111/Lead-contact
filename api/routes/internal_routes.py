"""
Internal API routes
These endpoints are called by Trigger.dev tasks (not by frontend)
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from db.repository_factory import (
    get_email_log_repository, 
    get_conversation_repository, 
    get_campaign_repository,
    get_provider_token_repository,
    get_prompt_repository
)
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
    gmail_message_id: Optional[str] = None
    gmail_thread_id: Optional[str] = None


@router.post("/email-logs")
async def create_email_log(request: CreateEmailLogRequest):
    """
    Create email log entry
    Called by Trigger.dev after sending each email
    """
    try:
        log_repo = await get_email_log_repository()
        conv_repo = await get_conversation_repository()
        
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
            sent_at=sent_at,
            gmail_message_id=request.gmail_message_id,
            gmail_thread_id=request.gmail_thread_id
        )
        
        # If sent successfully and we have a thread ID, create a conversation
        if request.status == "sent" and request.gmail_thread_id:
            try:
                # Check if conversation already exists for this thread
                existing = await conv_repo.get_by_thread_id(request.gmail_thread_id)
                
                if not existing:
                    # Create new conversation
                    conversation = await conv_repo.create_conversation(
                        user_id=request.user_id,
                        campaign_id=request.campaign_id,
                        email_log_id=log.id,
                        contact_email=request.to_email,
                        gmail_thread_id=request.gmail_thread_id
                    )
                    
                    # Add the initial message to conversation
                    await conv_repo.add_message(
                        conversation_id=conversation.id,
                        campaign_id=request.campaign_id,
                        direction="outbound",
                        from_email="me",
                        to_email=request.to_email,
                        subject=request.subject,
                        body=request.body,
                        gmail_message_id=request.gmail_message_id or "",
                        is_auto_reply=False,
                        sent_at=sent_at
                    )
                    logger.info(f"Created conversation for thread {request.gmail_thread_id}")
            except Exception as conv_error:
                logger.error(f"Error creating conversation: {str(conv_error)}")
        
        return {
            "success": True,
            "log_id": log.id,
            "gmail_thread_id": request.gmail_thread_id
        }
        
    except Exception as e:
        logger.error(f"Error creating email log: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auto-reply-campaigns")
async def get_auto_reply_campaigns(user_id: str = Query(...)):
    """Get campaigns with auto-reply enabled for a user"""
    try:
        campaign_repo = await get_campaign_repository()
        prompt_repo = await get_prompt_repository()
        campaigns = await campaign_repo.get_campaigns_with_auto_reply(user_id)
        
        result_campaigns = []
        for c in campaigns:
            # Fetch prompt text if campaign has a prompt_id
            prompt_text = None
            if c.prompt_id:
                prompt = await prompt_repo.get_by_id(c.prompt_id)
                if prompt:
                    prompt_text = prompt.prompt_text
            
            result_campaigns.append({
                "id": c.id,
                "user_id": c.user_id,
                "auto_reply_enabled": c.auto_reply_enabled,
                "auto_reply_subject": c.auto_reply_subject,
                "auto_reply_body": c.auto_reply_body,
                "max_replies_per_thread": c.max_replies_per_thread,
                "prompt_id": c.prompt_id,
                "prompt_text": prompt_text,  # Custom prompt text (None = use system default)
            })
        
        return {"campaigns": result_campaigns}
    except Exception as e:
        logger.error(f"Error fetching auto-reply campaigns: {str(e)}")
        return {"campaigns": []}


@router.get("/conversations/{campaign_id}")
async def get_campaign_conversations(campaign_id: str):
    """Get active conversations for a campaign"""
    try:
        conv_repo = await get_conversation_repository()
        conversations = await conv_repo.get_active_conversations_for_campaign(campaign_id)
        
        return {
            "conversations": [
                {
                    "id": c.id,
                    "gmail_thread_id": c.gmail_thread_id,
                    "contact_email": c.contact_email,
                    "auto_replies_sent": c.auto_replies_sent,
                    "status": c.status,
                }
                for c in conversations
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching conversations: {str(e)}")
        return {"conversations": []}


@router.get("/message-exists/{gmail_message_id}")
async def check_message_exists(gmail_message_id: str):
    """Check if a message has already been processed"""
    try:
        conv_repo = await get_conversation_repository()
        exists = await conv_repo.message_exists(gmail_message_id)
        return {"exists": exists}
    except Exception as e:
        logger.error(f"Error checking message: {str(e)}")
        return {"exists": False}


class RecordReplyRequest(BaseModel):
    """Request to record an inbound reply"""
    conversation_id: str
    campaign_id: str
    gmail_message_id: str
    from_email: str
    subject: str
    body: str
    replied_at: str


@router.post("/record-reply")
async def record_reply(request: RecordReplyRequest):
    """Record an inbound reply from contact"""
    try:
        conv_repo = await get_conversation_repository()
        campaign_repo = await get_campaign_repository()
        
        # Parse replied_at
        replied_at = datetime.utcnow()
        try:
            replied_at = datetime.fromisoformat(request.replied_at.replace('Z', '+00:00'))
        except:
            pass
        
        # Add message to conversation
        await conv_repo.add_message(
            conversation_id=request.conversation_id,
            campaign_id=request.campaign_id,
            direction="inbound",
            from_email=request.from_email,
            to_email="me",
            subject=request.subject,
            body=request.body,
            gmail_message_id=request.gmail_message_id,
            is_auto_reply=False,
            sent_at=replied_at
        )
        
        # Update conversation
        await conv_repo.update_on_reply(request.conversation_id, is_inbound=True)
        
        # Increment campaign replies count
        await campaign_repo.increment_replies_count(request.campaign_id)
        
        logger.info(f"Recorded reply from {request.from_email}")
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error recording reply: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class RecordAutoReplyRequest(BaseModel):
    """Request to record an auto-reply that was sent"""
    conversation_id: str
    campaign_id: str
    gmail_message_id: str
    to_email: str
    subject: str
    body: str


@router.post("/record-auto-reply")
async def record_auto_reply(request: RecordAutoReplyRequest):
    """Record an auto-reply that was sent"""
    try:
        conv_repo = await get_conversation_repository()
        
        # Add message to conversation
        await conv_repo.add_message(
            conversation_id=request.conversation_id,
            campaign_id=request.campaign_id,
            direction="outbound",
            from_email="me",
            to_email=request.to_email,
            subject=request.subject,
            body=request.body,
            gmail_message_id=request.gmail_message_id,
            is_auto_reply=True,
            sent_at=datetime.utcnow()
        )
        
        # Increment auto-reply count
        await conv_repo.increment_auto_replies(request.conversation_id)
        
        logger.info(f"Recorded auto-reply to {request.to_email}")
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error recording auto-reply: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users-with-auto-reply")
async def get_users_with_auto_reply():
    """
    Get all users that have campaigns with auto-reply enabled
    Returns user IDs with their Gmail tokens for scheduled task
    """
    try:
        campaign_repo = await get_campaign_repository()
        token_repo = await get_provider_token_repository()
        
        # Get all campaigns with auto-reply enabled
        campaigns = await campaign_repo.get_all_auto_reply_campaigns()
        
        # Get unique user IDs
        user_ids = list(set(c.user_id for c in campaigns))
        
        # Fetch tokens for each user
        users_with_tokens = []
        for user_id in user_ids:
            token = await token_repo.get_by_user_and_provider(user_id, "google")
            if token:
                users_with_tokens.append({
                    "user_id": user_id,
                    "access_token": token.access_token,
                    "refresh_token": token.refresh_token,
                    "token_expiry": token.expiry.isoformat() if token.expiry else None
                })
        
        return {"users": users_with_tokens}
        
    except Exception as e:
        logger.error(f"Error fetching users with auto-reply: {str(e)}")
        return {"users": []}


@router.get("/conversation-history/{conversation_id}")
async def get_conversation_history(conversation_id: str):
    """
    Get conversation history for AI context
    Returns messages in chronological order
    """
    try:
        conv_repo = await get_conversation_repository()
        
        messages = await conv_repo.get_messages(conversation_id)
        
        return {
            "messages": [
                {
                    "direction": msg.direction,
                    "subject": msg.subject,
                    "body": msg.body[:500] if msg.body else "",  # Truncate for context
                    "is_auto_reply": msg.is_auto_reply,
                    "sent_at": msg.sent_at.isoformat() if msg.sent_at else None
                }
                for msg in messages
            ]
        }
        
    except Exception as e:
        logger.error(f"Error fetching conversation history: {str(e)}")
        return {"messages": []}

