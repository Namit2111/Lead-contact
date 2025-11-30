"""
Cal.com API Client
Documentation: https://developer.cal.com/api
"""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from utils.logger import logger


class CalComClient:
    """Client for interacting with Cal.com API"""

    BASE_URL = "https://api.cal.com/v1"

    def __init__(self, api_key: str):
        """Initialize Cal.com client with API key"""
        self.api_key = api_key
        # Mask API key for logging (show first 8 and last 4 chars)
        masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
        logger.info(f"Initializing Cal.com client with API key: {masked_key} (length: {len(api_key)})")
        
        # Cal.com API uses apiKey as query parameter (not header)
        self.headers = {
            "Content-Type": "application/json"
        }
        # Query parameter will be added per-request
        logger.debug(f"Cal.com headers: Content-Type=application/json (apiKey will be in query params)")

    async def get_me(self) -> Dict[str, Any]:
        """Get current user info"""
        # Cal.com API uses apiKey as query parameter
        url = f"{self.BASE_URL}/me"
        params = {"apiKey": self.api_key}
        logger.info(f"Cal.com API Request: GET {url}")
        logger.debug(f"Request params: apiKey={self.api_key[:8]}...{self.api_key[-4:]}")
        logger.debug(f"Request headers: {list(self.headers.keys())}")
        
        async with httpx.AsyncClient() as client:
            try:
                # Try with query parameter (Cal.com standard)
                response = await client.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=10.0
                )
                logger.info(f"Cal.com API Response: Status {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                
                # Log response body for debugging
                try:
                    response_body = response.json()
                    logger.debug(f"Response body: {response_body}")
                except:
                    response_text = response.text[:500]  # First 500 chars
                    logger.debug(f"Response text: {response_text}")
                
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Cal.com API HTTP Error: {e.response.status_code}")
                logger.error(f"Request URL: {e.request.url}")
                logger.error(f"Request method: {e.request.method}")
                logger.error(f"Request headers: {dict(e.request.headers)}")
                try:
                    error_body = e.response.json()
                    logger.error(f"Error response body: {error_body}")
                except:
                    error_text = e.response.text
                    logger.error(f"Error response text: {error_text}")
                raise
            except Exception as e:
                logger.error(f"Cal.com API Exception: {type(e).__name__}: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise

    async def get_event_types(self) -> List[Dict[str, Any]]:
        """Get all event types for the user"""
        url = f"{self.BASE_URL}/event-types"
        params = {"apiKey": self.api_key}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                params=params,
                headers=self.headers,
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("event_types", [])

    async def get_availability(
        self,
        event_type_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        timezone: str = "UTC"
    ) -> List[Dict[str, Any]]:
        """
        Get available time slots for an event type
        
        Args:
            event_type_id: The event type ID
            start_date: Start date (defaults to today)
            end_date: End date (defaults to 7 days from start)
            timezone: Timezone (defaults to UTC)
        """
        if not start_date:
            start_date = datetime.utcnow()
        if not end_date:
            end_date = start_date + timedelta(days=7)

        params = {
            "eventTypeId": event_type_id,
            "startTime": start_date.isoformat(),
            "endTime": end_date.isoformat(),
            "timeZone": timezone
        }

        # Add apiKey to params
        params["apiKey"] = self.api_key
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/slots/available",
                headers=self.headers,
                params=params,
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("slots", [])

    async def create_booking(
        self,
        event_type_id: int,
        start_time: datetime,
        end_time: datetime,
        attendee_email: str,
        attendee_name: str,
        notes: Optional[str] = None,
        timezone: str = "UTC"
    ) -> Dict[str, Any]:
        """
        Create a booking directly
        
        Args:
            event_type_id: The event type ID
            start_time: Booking start time
            end_time: Booking end time
            attendee_email: Attendee email
            attendee_name: Attendee name
            notes: Optional notes
            timezone: Timezone
        """
        payload = {
            "eventTypeId": event_type_id,
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "responses": {
                "email": attendee_email,
                "name": attendee_name,
                "notes": notes or ""
            },
            "timeZone": timezone
        }

        # Add apiKey to payload or use query param
        url = f"{self.BASE_URL}/bookings"
        params = {"apiKey": self.api_key}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params=params,
                headers=self.headers,
                json=payload,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()

    async def test_connection(self) -> bool:
        """Test if API key is valid"""
        logger.info("Testing Cal.com connection...")
        masked_key = f"{self.api_key[:8]}...{self.api_key[-4:]}" if len(self.api_key) > 12 else "***"
        logger.info(f"Using API key: {masked_key} (length: {len(self.api_key)})")
        
        try:
            result = await self.get_me()
            logger.info(f"✅ Cal.com connection test successful! User: {result.get('username', 'unknown')}")
            return True
        except httpx.HTTPStatusError as e:
            logger.error("="*60)
            logger.error("Cal.com connection test FAILED - HTTP Error")
            logger.error(f"Status Code: {e.response.status_code}")
            logger.error(f"Request URL: {e.request.url}")
            logger.error(f"Request Method: {e.request.method}")
            
            # Log request headers (mask API key)
            req_headers = dict(e.request.headers)
            if 'Authorization' in req_headers:
                auth_header = req_headers['Authorization']
                masked_auth = f"{auth_header[:20]}...{auth_header[-10:]}" if len(auth_header) > 30 else "***"
                req_headers['Authorization'] = masked_auth
            logger.error(f"Request Headers: {req_headers}")
            
            # Log response details
            logger.error(f"Response Headers: {dict(e.response.headers)}")
            try:
                error_body = e.response.json()
                logger.error(f"Response Body (JSON): {error_body}")
            except:
                error_text = e.response.text
                logger.error(f"Response Body (Text): {error_text[:500]}")
            
            logger.error("="*60)
            
            if e.response.status_code == 401:
                logger.error("❌ Cal.com connection test failed: Invalid API key (401 Unauthorized)")
                logger.error("💡 Possible causes:")
                logger.error("   1. API key is incorrect or has been revoked")
                logger.error("   2. API key format is wrong (should be plain string, not prefixed)")
                logger.error("   3. API key doesn't have required permissions")
                logger.error("   4. Cal.com API endpoint changed")
            else:
                logger.error(f"❌ Cal.com connection test failed: HTTP {e.response.status_code}")
            return False
        except Exception as e:
            logger.error("="*60)
            logger.error("Cal.com connection test FAILED - Exception")
            logger.error(f"Exception Type: {type(e).__name__}")
            logger.error(f"Exception Message: {str(e)}")
            import traceback
            logger.error(f"Full Traceback:\n{traceback.format_exc()}")
            logger.error("="*60)
            return False

