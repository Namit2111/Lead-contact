from fastapi import APIRouter, Header, HTTPException
from typing import Optional, List
from datetime import datetime, timedelta
import httpx

from db.mongodb.calendar_repository import MongoCalendarRepository
from integrations.calcom_client import CalComClient
from utils.logger import logger
from core.calendar.models import (
    ConnectCalendarRequest,
    CalendarStatusResponse,
    EventTypeItem,
    EventTypesResponse,
    UpdateEventTypeRequest,
    CalendarSlot,
    AvailabilityResponse,
    BookMeetingRequest,
    BookingResponse,
    ToggleCalToolsRequest
)


router = APIRouter(prefix="/calendar")


def get_user_id_from_header(x_user_id: Optional[str] = Header(None)) -> str:
    """Extract user ID from header"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User authentication required. Missing X-User-Id header")
    return x_user_id


# works fine 
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
                    request.event_type_slug = first_type.get("slug") or first_type.get("slugPath")
                    request.event_type_name = first_type.get("title") or first_type.get("name")
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
            event_type_name=token["event_type_name"],
            cal_tools_enabled=token.get("cal_tools_enabled", True)
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


def _get_event_type_from_token(token: dict, client: CalComClient):
    """Return event type info, fetching first event if missing"""
    return token.get("event_type_id"), token.get("event_type_slug"), token.get("event_type_name")


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
            event_type_name=token["event_type_name"],
            cal_tools_enabled=token.get("cal_tools_enabled", True)
        )

    except Exception as e:
        logger.error(f"Error getting calendar status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/toggle-tools", response_model=CalendarStatusResponse)
async def toggle_calendar_tools(
    request: ToggleCalToolsRequest,
    x_user_id: Optional[str] = Header(None)
):
    """Toggle AI calendar tools (get availability, book meetings)"""
    user_id = get_user_id_from_header(x_user_id)

    try:
        calendar_repo = MongoCalendarRepository()
        token = await calendar_repo.get_by_user(user_id, "cal.com")

        if not token:
            raise HTTPException(status_code=404, detail="Calendar not connected")

        updated = await calendar_repo.toggle_cal_tools(user_id, request.enabled)

        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update toggle")

        return CalendarStatusResponse(
            connected=True,
            provider="cal.com",
            username=updated["username"],
            event_type_id=updated["event_type_id"],
            event_type_slug=updated["event_type_slug"],
            event_type_name=updated["event_type_name"],
            cal_tools_enabled=updated["cal_tools_enabled"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling calendar tools: {str(e)}")
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
                slug=et.get("slug", "") or et.get("slugPath", ""),
                title=et.get("title", "") or et.get("name", ""),
                length=et.get("length", 30) or et.get("duration", 30),
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


@router.get("/availability", response_model=AvailabilityResponse)
async def get_availability(
    days: int = 14,
    timezone: str = "UTC",
    x_user_id: Optional[str] = Header(None)
):
    """Get available slots for the stored Cal.com connection"""
    user_id = get_user_id_from_header(x_user_id)

    try:
        calendar_repo = MongoCalendarRepository()
        token = await calendar_repo.get_by_user(user_id, "cal.com")

        if not token:
            return AvailabilityResponse(
                connected=False,
                error="Calendar not connected"
            )

        client = CalComClient(token["api_key"])

        # Determine event type (fallback to first available) and capture duration if present
        event_type_id = token.get("event_type_id")
        event_type_name = token.get("event_type_name")
        event_type_slug = token.get("event_type_slug")
        event_type_duration = None

        event_types_cache = None

        if not event_type_id:
            event_types_cache = await client.get_event_types()
            if not event_types_cache:
                return AvailabilityResponse(
                    connected=False,
                    error="No event types found for this Cal.com account"
                )
            first_type = event_types_cache[0]
            event_type_id = first_type.get("id")
            event_type_name = first_type.get("title") or first_type.get("name")
            event_type_slug = first_type.get("slug") or first_type.get("slugPath")
            event_type_duration = first_type.get("length") or first_type.get("duration")
        else:
            # Try to fetch duration for this event type
            try:
                event_types_cache = await client.get_event_types()
                for et in event_types_cache or []:
                    if et.get("id") == event_type_id:
                        event_type_duration = et.get("length") or et.get("duration")
                        if not event_type_name:
                            event_type_name = et.get("title") or et.get("name")
                        if not event_type_slug:
                            event_type_slug = et.get("slug") or et.get("slugPath")
                        break
            except Exception:
                event_type_duration = None

        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=max(1, days))

        slots = await client.get_availability(
            event_type_id=event_type_id,
            start_date=start_date,
            end_date=end_date,
            timezone=timezone,
            duration=event_type_duration
        )

        def _parse_iso(value: str) -> datetime:
            if value.endswith("Z"):
                value = value.replace("Z", "+00:00")
            return datetime.fromisoformat(value)

        formatted_slots = []
        default_duration = event_type_duration or 30

        for slot in slots:
            start_raw = slot.get("start") or slot.get("time")
            end_raw = slot.get("end") or slot.get("endTime")
            slot_tz = slot.get("timeZone") or slot.get("time_zone") or timezone
            if not start_raw:
                continue
            start_dt = _parse_iso(start_raw)
            if end_raw:
                end_dt = _parse_iso(end_raw)
            else:
                end_dt = start_dt + timedelta(minutes=default_duration)

            formatted_slots.append(
                CalendarSlot(
                    start=start_dt,
                    end=end_dt,
                    time_zone=slot_tz
                )
            )

        return AvailabilityResponse(
            connected=True,
            event_type_id=event_type_id,
            event_type_name=event_type_name,
            booking_link=f"https://cal.com/{token.get('username')}/{event_type_slug}" if event_type_slug else None,
            slots=formatted_slots
        )

    except httpx.HTTPStatusError as e:
        logger.error(f"Cal.com API error: HTTP {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 401:
            raise HTTPException(status_code=400, detail="Invalid Cal.com API key. Please reconnect your calendar.")
        raise HTTPException(status_code=400, detail=f"Cal.com API error: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting availability: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/book", response_model=BookingResponse)
async def book_meeting(
    request: BookMeetingRequest,
    x_user_id: Optional[str] = Header(None)
):
    """Book a meeting using stored Cal.com credentials"""
    user_id = get_user_id_from_header(x_user_id)

    try:
        calendar_repo = MongoCalendarRepository()
        token = await calendar_repo.get_by_user(user_id, "cal.com")

        if not token:
            raise HTTPException(status_code=404, detail="Calendar not connected")

        client = CalComClient(token["api_key"])

        event_type_id = request.event_type_id or token.get("event_type_id")
        if not event_type_id:
            event_types = await client.get_event_types()
            if not event_types:
                raise HTTPException(status_code=400, detail="No event types available to book")
            event_type_id = event_types[0].get("id")

        result = await client.create_booking(
            event_type_id=event_type_id,
            start_time=request.start,
            end_time=request.end,
            attendee_email=request.attendee_email,
            attendee_name=request.attendee_name,
            notes=request.notes,
            timezone=request.time_zone
        )

        booking_data = result.get("data", result)

        return BookingResponse(
            success=True,
            booking_id=str(booking_data.get("id")) if booking_data.get("id") else None,
            booking_url=booking_data.get("url") or booking_data.get("bookingUrl")
        )

    except httpx.HTTPStatusError as e:
        logger.error(f"Cal.com API error: HTTP {e.response.status_code} - {e.response.text}")
        detail = e.response.text
        if e.response.status_code == 401:
            detail = "Invalid Cal.com API key. Please reconnect your calendar."
        raise HTTPException(status_code=400, detail=detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error booking meeting: {str(e)}")
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
            event_type_name=updated["event_type_name"],
            cal_tools_enabled=updated.get("cal_tools_enabled", True)
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

