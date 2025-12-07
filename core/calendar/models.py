from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

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


class CalendarSlot(BaseModel):
    """Single availability slot"""
    start: datetime
    end: datetime
    time_zone: str = "UTC"


class AvailabilityResponse(BaseModel):
    """Available slots for a user's calendar"""
    connected: bool
    event_type_id: Optional[int] = None
    event_type_name: Optional[str] = None
    booking_link: Optional[str] = None
    slots: List[CalendarSlot] = Field(default_factory=list)
    error: Optional[str] = None


class BookMeetingRequest(BaseModel):
    """Request to book a meeting"""
    event_type_id: Optional[int] = None
    start: datetime
    end: datetime
    attendee_email: str
    attendee_name: str
    notes: Optional[str] = None
    time_zone: str = "UTC"


class BookingResponse(BaseModel):
    """Response for booking creation"""
    success: bool
    booking_id: Optional[str] = None
    booking_url: Optional[str] = None
    error: Optional[str] = None
