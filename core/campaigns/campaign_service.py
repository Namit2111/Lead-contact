import uuid
from datetime import datetime
from typing import List, Dict, Any
from core.templates.template_service import TemplateService
from providers.gmail.gmail_send_service import GmailSendService
from db.repository_factory import (
    get_contact_repository,
    get_template_repository,
    get_provider_token_repository,
    get_email_log_repository
)
from core.auth.token_refresher import TokenRefresher
from utils.logger import logger


class CampaignService:
    """Service for managing email campaigns"""

    @staticmethod
    async def send_campaign(
        user_id: str,
        csv_source: str,
        template_id: str
    ) -> Dict[str, Any]:
        """
        Send email campaign to all contacts in a CSV source
        
        Args:
            user_id: User ID
            csv_source: CSV filename/source
            template_id: Template ID to use
            
        Returns:
            Campaign results with stats
        """
        campaign_id = str(uuid.uuid4())
        
        try:
            # Get repositories
            contact_repo = await get_contact_repository()
            template_repo = await get_template_repository()
            token_repo = await get_provider_token_repository()
            log_repo = await get_email_log_repository()
            
            # Get template
            template = await template_repo.get_by_id(template_id)
            if not template:
                raise ValueError("Template not found")
            if template.user_id != user_id:
                raise ValueError("Access denied to template")
            
            # Get contacts from CSV source
            contacts = await contact_repo.get_contacts_by_source(
                user_id, csv_source, skip=0, limit=1000
            )
            
            if not contacts:
                raise ValueError(f"No contacts found in {csv_source}")
            
            # Get user's OAuth token
            provider_token = await token_repo.get_by_user_and_provider(user_id, "google")
            if not provider_token:
                raise ValueError("No Google account connected. Please connect your Gmail account.")
            
            # Get access token (refresh if needed)
            # For now, just use the access token directly
            # TODO: Implement token refresh check
            access_token = provider_token.access_token
            
            # Send emails
            results = {
                "campaign_id": campaign_id,
                "total": len(contacts),
                "sent": 0,
                "failed": 0,
                "errors": []
            }
            
            logger.info(f"Starting campaign {campaign_id} for {len(contacts)} contacts")
            
            for contact in contacts:
                try:
                    # Prepare contact data for template
                    contact_data = {
                        "name": contact.name or "there",
                        "email": contact.email,
                        "company": contact.company or "",
                        "phone": contact.phone or "",
                        **contact.custom_fields
                    }
                    
                    # Render template
                    rendered_subject = TemplateService.render_template(
                        template.subject, contact_data
                    )
                    rendered_body = TemplateService.render_template(
                        template.body, contact_data
                    )
                    
                    # Send email
                    await GmailSendService.send_email(
                        access_token=access_token,
                        to=contact.email,
                        subject=rendered_subject,
                        body=rendered_body
                    )
                    
                    # Log success
                    await log_repo.create_log(
                        user_id=user_id,
                        campaign_id=campaign_id,
                        contact_id=contact.id,
                        template_id=template_id,
                        to_email=contact.email,
                        subject=rendered_subject,
                        body=rendered_body,
                        status="sent",
                        sent_at=datetime.utcnow()
                    )
                    
                    results["sent"] += 1
                    logger.info(f"Sent email to {contact.email}")
                    
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Failed to send to {contact.email}: {error_msg}")
                    
                    # Log failure
                    await log_repo.create_log(
                        user_id=user_id,
                        campaign_id=campaign_id,
                        contact_id=contact.id,
                        template_id=template_id,
                        to_email=contact.email,
                        subject=template.subject,
                        body=template.body,
                        status="failed",
                        error_message=error_msg
                    )
                    
                    results["failed"] += 1
                    results["errors"].append({
                        "email": contact.email,
                        "error": error_msg
                    })
            
            logger.info(f"Campaign {campaign_id} completed: {results['sent']} sent, {results['failed']} failed")
            return results
            
        except Exception as e:
            logger.error(f"Campaign {campaign_id} failed: {str(e)}")
            raise

    @staticmethod
    async def preview_campaign(
        user_id: str,
        csv_source: str,
        template_id: str
    ) -> Dict[str, Any]:
        """
        Preview how emails will look for first contact in CSV
        
        Args:
            user_id: User ID
            csv_source: CSV filename/source
            template_id: Template ID to use
            
        Returns:
            Preview with rendered subject and body
        """
        try:
            # Get repositories
            contact_repo = await get_contact_repository()
            template_repo = await get_template_repository()
            
            # Get template
            template = await template_repo.get_by_id(template_id)
            if not template:
                raise ValueError("Template not found")
            if template.user_id != user_id:
                raise ValueError("Access denied to template")
            
            # Get first contact from CSV source
            contacts = await contact_repo.get_contacts_by_source(
                user_id, csv_source, skip=0, limit=1
            )
            
            if not contacts:
                raise ValueError(f"No contacts found in {csv_source}")
            
            contact = contacts[0]
            
            # Prepare contact data
            contact_data = {
                "name": contact.name or "there",
                "email": contact.email,
                "company": contact.company or "",
                "phone": contact.phone or "",
                **contact.custom_fields
            }
            
            # Render template
            rendered_subject = TemplateService.render_template(
                template.subject, contact_data
            )
            rendered_body = TemplateService.render_template(
                template.body, contact_data
            )
            
            return {
                "to": contact.email,
                "subject": rendered_subject,
                "body": rendered_body,
                "contact_name": contact.name,
                "template_name": template.name
            }
            
        except Exception as e:
            logger.error(f"Preview failed: {str(e)}")
            raise

