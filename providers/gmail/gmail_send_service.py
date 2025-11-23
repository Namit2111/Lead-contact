import httpx
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
from utils.logger import logger


class GmailSendService:
    """Service for sending emails via Gmail API"""

    GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"

    @staticmethod
    def create_message(to: str, subject: str, body: str, from_email: str = None) -> Dict[str, Any]:
        """
        Create a MIME message for Gmail API
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text or HTML)
            from_email: Sender email (optional, defaults to authenticated user)
            
        Returns:
            Dictionary with base64 encoded message
        """
        message = MIMEMultipart('alternative')
        message['To'] = to
        message['Subject'] = subject
        
        if from_email:
            message['From'] = from_email
        
        # Add plain text and HTML parts
        text_part = MIMEText(body, 'plain')
        html_part = MIMEText(body.replace('\n', '<br>'), 'html')
        
        message.attach(text_part)
        message.attach(html_part)
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        return {'raw': raw_message}

    @staticmethod
    async def send_email(
        access_token: str,
        to: str,
        subject: str,
        body: str,
        from_email: str = None
    ) -> Dict[str, Any]:
        """
        Send email via Gmail API
        
        Args:
            access_token: OAuth access token
            to: Recipient email address
            subject: Email subject
            body: Email body
            from_email: Sender email (optional)
            
        Returns:
            Gmail API response with message ID
            
        Raises:
            httpx.HTTPError: If sending fails
        """
        try:
            # Create message
            message = GmailSendService.create_message(to, subject, body, from_email)
            
            # Send via Gmail API
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    GmailSendService.GMAIL_SEND_URL,
                    headers=headers,
                    json=message,
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Email sent successfully to {to}, message ID: {result.get('id')}")
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to send email to {to}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending email to {to}: {str(e)}")
            raise

    @staticmethod
    async def send_batch_emails(
        access_token: str,
        emails: list[Dict[str, str]],
        from_email: str = None
    ) -> Dict[str, Any]:
        """
        Send multiple emails (sequentially for now)
        
        Args:
            access_token: OAuth access token
            emails: List of dicts with 'to', 'subject', 'body'
            from_email: Sender email (optional)
            
        Returns:
            Dictionary with success/failure counts
        """
        results = {
            "total": len(emails),
            "sent": 0,
            "failed": 0,
            "errors": []
        }
        
        for email in emails:
            try:
                await GmailSendService.send_email(
                    access_token=access_token,
                    to=email['to'],
                    subject=email['subject'],
                    body=email['body'],
                    from_email=from_email
                )
                results["sent"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "to": email['to'],
                    "error": str(e)
                })
                logger.error(f"Failed to send to {email['to']}: {str(e)}")
        
        return results

