import httpx
from typing import Optional, Dict, Any
from config import settings
from utils.logger import logger


class TriggerClient:
    """Client for Trigger.dev API"""
    
    def __init__(self):
        # Use tr_dev_... for local testing, tr_prod_... for production
        self.api_key = getattr(settings, 'trigger_api_key')
        self.api_url = getattr(settings, 'TRIGGER_API_URL', 'https://api.trigger.dev')
  
        if not self.api_key:
            logger.warning("TRIGGER_API_KEY not set in environment variables")
    
    async def trigger_campaign(
        self,
        campaign_id: str,
        user_id: str,
        csv_source: str,
        template_id: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_expiry: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Trigger email campaign job in Trigger.dev
        
        Args:
            campaign_id: Campaign ID
            user_id: User ID
            csv_source: CSV filename/source
            template_id: Template ID
            access_token: Gmail access token
            refresh_token: Gmail refresh token (for long-running campaigns)
            token_expiry: Token expiry timestamp (ISO format)
            
        Returns:
            Trigger.dev response with run ID
        """
        if not self.api_key:
            raise ValueError("Trigger.dev API key not configured")
        
        try:
            # Build the task payload
            task_payload = {
                "campaignId": campaign_id,
                "userId": user_id,
                "csvSource": csv_source,
                "templateId": template_id,
                "accessToken": access_token,
                "backendUrl": settings.backend_url
            }
            
            # Add refresh token and expiry if provided (for token refresh support)
            if refresh_token:
                task_payload["refreshToken"] = refresh_token
            if token_expiry:
                task_payload["tokenExpiry"] = token_expiry
            
            # Wrap in 'payload' key as required by Trigger.dev REST API
            request_body = {
                "payload": task_payload
            }
            
            logger.info(f"Triggering campaign with payload: {task_payload}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}/api/v1/tasks/send-email-campaign/trigger",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=request_body
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Triggered campaign {campaign_id} in Trigger.dev: {result.get('id')}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error triggering campaign: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"Failed to trigger campaign: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Request error triggering campaign: {str(e)}")
            raise ValueError(f"Failed to connect to Trigger.dev: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error triggering campaign: {str(e)}")
            raise
    
    async def get_run_status(self, run_id: str) -> Dict[str, Any]:
        """
        Get status of a Trigger.dev run
        
        Args:
            run_id: Trigger.dev run ID
            
        Returns:
            Run status information
        """
        if not self.api_key:
            raise ValueError("Trigger.dev API key not configured")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.api_url}/api/v1/runs/{run_id}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}"
                    }
                )
                
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error getting run status: {str(e)}")
            raise
    
    async def cancel_run(self, run_id: str) -> Dict[str, Any]:
        """
        Cancel a Trigger.dev run
        
        Args:
            run_id: Trigger.dev run ID
            
        Returns:
            Cancellation response
        """
        if not self.api_key:
            raise ValueError("Trigger.dev API key not configured")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}/api/v1/runs/{run_id}/cancel",
                    headers={
                        "Authorization": f"Bearer {self.api_key}"
                    }
                )
                
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error cancelling run: {str(e)}")
            raise


# Global client instance
trigger_client = TriggerClient()

