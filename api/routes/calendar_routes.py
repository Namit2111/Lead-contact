from fastapi import APIRouter, Header, HTTPException
from typing import Optional
from pydantic import BaseModel
import httpx
from db.mongodb.calendar_repository import MongoCalendarRepository
from integrations.calcom_client import CalComClient
from utils.logger import logger


router = APIRouter(prefix="/calendar")


# Request/Response Models
class ConnectCalendarRequest(BaseModel):
    """Request to connect calendar"""
    api_key: str
    event_type_id: Optional[int] = None
    event_type_slug: Optional[str] = None
    event_type_name: Optional[str] = None


class CalendarStatusResponse(BaseModel):
    """Response with calendar connection status"""
    connected: bool
    provider: Optional[str] = None
    username: Optional[str] = None
    event_type_id: Optional[int] = None
    event_type_slug: Optional[str] = None
    event_type_name: Optional[str] = None


class EventTypeItem(BaseModel):
    """Single event type"""
    id: int
    slug: str
    title: str
    length: int  # Duration in minutes
    description: Optional[str] = None


class EventTypesResponse(BaseModel):
    """Response with event types"""
    event_types: list[EventTypeItem]


class UpdateEventTypeRequest(BaseModel):
    """Request to update event type"""
    event_type_id: int
    event_type_slug: str
    event_type_name: str


def get_user_id_from_header(x_user_id: Optional[str] = Header(None)) -> str:
    """Extract user ID from header"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User authentication required. Missing X-User-Id header")
    return x_user_id


@router.post("/connect", response_model=CalendarStatusResponse)
async def connect_calendar(
    request: ConnectCalendarRequest,
    x_user_id: Optional[str] = Header(None)
):
    """Connect Cal.com calendar"""
    user_id = get_user_id_from_header(x_user_id)

    try:
        # Log incoming request details
        api_key_length = len(request.api_key) if request.api_key else 0
        masked_key = f"{request.api_key[:8]}...{request.api_key[-4:]}" if api_key_length > 12 else "***"
        logger.info(f"Calendar connect request - User ID: {user_id}, API Key length: {api_key_length}, Masked: {masked_key}")
        logger.debug(f"Full API key received: {request.api_key}")
        logger.debug(f"Event type ID: {request.event_type_id}, Slug: {request.event_type_slug}, Name: {request.event_type_name}")
        
        # Test connection first
        client = CalComClient(request.api_key)
        if not await client.test_connection():
            raise HTTPException(
                status_code=400, 
                detail="Invalid Cal.com API key. Please check your API key at cal.com/settings/developer/api-keys"
            )

        # Get user info to extract username
        try:
            user_info = await client.get_me()
            username = user_info.get("username") or user_info.get("email", "").split("@")[0]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid Cal.com API key. Please check your API key at cal.com/settings/developer/api-keys"
                )
            raise

        # If event type not provided, get first available
        if not request.event_type_id:
            try:
                event_types = await client.get_event_types()
                if event_types:
                    first_type = event_types[0]
                    request.event_type_id = first_type.get("id")
                    request.event_type_slug = first_type.get("slug")
                    request.event_type_name = first_type.get("title")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid Cal.com API key. Please check your API key at cal.com/settings/developer/api-keys"
                    )
                raise

        # Save token
        calendar_repo = MongoCalendarRepository()
        token = await calendar_repo.save_calendar_token(
            user_id=user_id,
            provider="cal.com",
            api_key=request.api_key,
            username=username,
            event_type_id=request.event_type_id,
            event_type_slug=request.event_type_slug,
            event_type_name=request.event_type_name
        )

        return CalendarStatusResponse(
            connected=True,
            provider="cal.com",
            username=token["username"],
            event_type_id=token["event_type_id"],
            event_type_slug=token["event_type_slug"],
            event_type_name=token["event_type_name"]
        )

    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            logger.error("Cal.com API error: Invalid API key (401 Unauthorized)")
            raise HTTPException(
                status_code=400,
                detail="Invalid Cal.com API key. Please check your API key at cal.com/settings/developer/api-keys"
            )
        logger.error(f"Cal.com API error: HTTP {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=400, detail=f"Cal.com API error: {e.response.text}")
    except Exception as e:
        logger.error(f"Error connecting calendar: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=CalendarStatusResponse)
async def get_calendar_status(
    x_user_id: Optional[str] = Header(None)
):
    """Get calendar connection status"""
    user_id = get_user_id_from_header(x_user_id)

    try:
        calendar_repo = MongoCalendarRepository()
        token = await calendar_repo.get_by_user(user_id, "cal.com")

        if not token:
            return CalendarStatusResponse(connected=False)

        return CalendarStatusResponse(
            connected=True,
            provider="cal.com",
            username=token["username"],
            event_type_id=token["event_type_id"],
            event_type_slug=token["event_type_slug"],
            event_type_name=token["event_type_name"]
        )

    except Exception as e:
        logger.error(f"Error getting calendar status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/event-types", response_model=EventTypesResponse)
async def get_event_types(
    x_user_id: Optional[str] = Header(None)
):
    """Get available event types from Cal.com"""
    user_id = get_user_id_from_header(x_user_id)

    try:
        calendar_repo = MongoCalendarRepository()
        token = await calendar_repo.get_by_user(user_id, "cal.com")

        if not token:
            raise HTTPException(status_code=404, detail="Calendar not connected")

        client = CalComClient(token["api_key"])
        event_types = await client.get_event_types()

        event_items = [
            EventTypeItem(
                id=et.get("id"),
                slug=et.get("slug", ""),
                title=et.get("title", ""),
                length=et.get("length", 30),
                description=et.get("description")
            )
            for et in event_types
        ]

        return EventTypesResponse(event_types=event_items)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            logger.error("Cal.com API error: Invalid API key (401 Unauthorized)")
            raise HTTPException(
                status_code=400,
                detail="Invalid Cal.com API key. Please reconnect your calendar."
            )
        logger.error(f"Cal.com API error: HTTP {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=400, detail=f"Cal.com API error: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting event types: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/event-type", response_model=CalendarStatusResponse)
async def update_event_type(
    request: UpdateEventTypeRequest,
    x_user_id: Optional[str] = Header(None)
):
    """Update selected event type"""
    user_id = get_user_id_from_header(x_user_id)

    try:
        calendar_repo = MongoCalendarRepository()
        token = await calendar_repo.get_by_user(user_id, "cal.com")

        if not token:
            raise HTTPException(status_code=404, detail="Calendar not connected")

        updated = await calendar_repo.update_event_type(
            user_id=user_id,
            event_type_id=request.event_type_id,
            event_type_slug=request.event_type_slug,
            event_type_name=request.event_type_name
        )

        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update event type")

        return CalendarStatusResponse(
            connected=True,
            provider="cal.com",
            username=updated["username"],
            event_type_id=updated["event_type_id"],
            event_type_slug=updated["event_type_slug"],
            event_type_name=updated["event_type_name"]
        )

    except Exception as e:
        logger.error(f"Error updating event type: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/disconnect")
async def disconnect_calendar(
    x_user_id: Optional[str] = Header(None)
):
    """Disconnect calendar"""
    user_id = get_user_id_from_header(x_user_id)

    try:
        calendar_repo = MongoCalendarRepository()
        success = await calendar_repo.delete_by_user(user_id, "cal.com")

        if not success:
            raise HTTPException(status_code=404, detail="Calendar not connected")

        return {"success": True, "message": "Calendar disconnected"}

    except Exception as e:
        logger.error(f"Error disconnecting calendar: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

