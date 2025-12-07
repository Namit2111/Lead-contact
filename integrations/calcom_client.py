"""
Cal.com API Client (v2)
Documentation: https://developer.cal.com/api
"""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from utils.logger import logger


class CalComClient:
    """Client for interacting with Cal.com API v2."""

    # Cal.com uses header-based versioning; keep base without /v2
    BASE_URL = "https://api.cal.com/v2"
    # Documented version exposing slots/event-types/booking via header
    API_VERSION = "2024-06-14"

    def __init__(self, api_key: str):
        """Initialize Cal.com client with API key (Bearer)."""
        self.api_key = api_key
        masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
        logger.info(f"Initializing Cal.com client with API key: {masked_key} (length: {len(api_key)})")

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "cal-api-version": self.API_VERSION,
        }
        logger.debug("Cal.com headers prepared with bearer auth and version pin")

    async def _request(self, method: str, path: str, custom_headers: Optional[Dict[str, str]] = None, **kwargs) -> httpx.Response:
        """Internal helper for HTTP requests with consistent error logging."""
        url = f"{self.BASE_URL}{path}"
        # Merge custom headers with default headers (custom headers override defaults)
        headers = {**self.headers}
        if custom_headers:
            headers.update(custom_headers)
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(method, url, headers=headers, timeout=15.0, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                logger.error(f"Cal.com API HTTP Error: {e.response.status_code} for {method} {url}")
                try:
                    logger.error(f"Error body: {e.response.json()}")
                except Exception:
                    logger.error(f"Error text: {e.response.text[:500]}")
                raise
            except Exception as e:
                logger.error(f"Cal.com API Exception: {type(e).__name__}: {str(e)}")
                raise

    async def get_me(self) -> Dict[str, Any]:
        """Get current user info."""
        response = await self._request("GET", "/me")
        return response.json()

    async def get_event_types(self) -> List[Dict[str, Any]]:
        """Get all event types for the user."""
        response = await self._request("GET", "/event-types")
        data = response.json()
        return data.get("data") or data.get("event_types") or []

    async def get_availability(
        self,
        event_type_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        timezone: str = "UTC",
        duration: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get available time slots for an event type."""
        if not start_date:
            start_date = datetime.utcnow()
        if not end_date:
            end_date = start_date + timedelta(days=7)

        params = {
            "eventTypeId": event_type_id,
            "start": start_date.date().isoformat(),  # Date only: YYYY-MM-DD
            "end": end_date.date().isoformat(),  # Date only: YYYY-MM-DD
            "timeZone": timezone,
            "format": "range",  # return start/end when supported
        }
        if duration:
            params["duration"] = duration

        # v2 documented endpoint: /v2/slots
        # Override API version to 2024-09-04 for availability endpoint
        custom_headers = {"cal-api-version": "2024-09-04"}
        response = await self._request("GET", "/slots", params=params, custom_headers=custom_headers)
        data = response.json()
        slots_raw = data.get("slots") or data.get("data") or []

        # If data is returned as a date-indexed dict, flatten it
        if isinstance(slots_raw, dict):
            flat = []
            for date_key, slot_list in slots_raw.items():
                if not isinstance(slot_list, list):
                    continue
                for slot in slot_list:
                    # slot may just contain start time; keep date for context
                    if isinstance(slot, dict):
                        if "date" not in slot:
                            slot = {**slot, "date": date_key}
                        flat.append(slot)
            slots_raw = flat
        return slots_raw

    async def create_booking(
        self,
        event_type_id: int,
        start_time: datetime,
        end_time: datetime,
        attendee_email: str,
        attendee_name: str,
        notes: Optional[str] = None,
        timezone: str = "UTC",
    ) -> Dict[str, Any]:
        """Create a booking directly via v2 API."""
        # Format start time as ISO string (ensure Z suffix for UTC)
        start_iso = start_time.isoformat()
        # Replace +00:00 with Z for UTC times
        if start_iso.endswith('+00:00'):
            start_iso = start_iso.replace('+00:00', 'Z')
        elif start_iso.endswith('-00:00'):
            start_iso = start_iso.replace('-00:00', 'Z')
        # If naive datetime (no timezone), assume UTC and add Z
        elif '+' not in start_iso and not start_iso.endswith('Z'):
            start_iso += 'Z'
        
        payload = {
            "eventTypeId": event_type_id,
            "start": start_iso,
            "attendee": {
                "name": attendee_name,
                "email": attendee_email,
                "timeZone": timezone,
            }
        }

        # Override API version to 2024-08-13 for booking endpoint
        custom_headers = {"cal-api-version": "2024-08-13"}
        response = await self._request("POST", "/bookings", json=payload, custom_headers=custom_headers)
        return response.json()

    async def test_connection(self) -> bool:
        """Test if API key is valid."""
        logger.info("Testing Cal.com connection...")
        try:
            result = await self.get_me()
            logger.info(f"✅ Cal.com connection test successful! User: {result.get('username', 'unknown')}")
            return True
        except Exception:
            logger.error("❌ Cal.com connection test failed")
            return False

