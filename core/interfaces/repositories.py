from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from bson import ObjectId


class User:
    """User domain model"""
    def __init__(self, id: str, email: str, name: str, created_at: datetime):
        self.id = id
        self.email = email
        self.name = name
        self.created_at = created_at


class ProviderToken:
    """Provider token domain model"""
    def __init__(
        self,
        id: str,
        user_id: str,
        provider: str,
        access_token: str,
        refresh_token: str,
        expiry: datetime,
        scope: List[str],
        created_at: datetime,
        updated_at: datetime
    ):
        self.id = id
        self.user_id = user_id
        self.provider = provider
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expiry = expiry
        self.scope = scope
        self.created_at = created_at
        self.updated_at = updated_at


class UserRepository(ABC):
    """Abstract repository for user operations"""

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address"""
        pass

    @abstractmethod
    async def create_user(self, email: str, name: str) -> User:
        """Create a new user"""
        pass


class ProviderTokenRepository(ABC):
    """Abstract repository for provider token operations"""

    @abstractmethod
    async def save_tokens(
        self,
        user_id: str,
        provider: str,
        access_token: str,
        refresh_token: str,
        expiry: datetime,
        scope: List[str]
    ) -> ProviderToken:
        """Save provider tokens for a user"""
        pass

    @abstractmethod
    async def get_by_user_and_provider(self, user_id: str, provider: str) -> Optional[ProviderToken]:
        """Get provider tokens by user and provider"""
        pass

    @abstractmethod
    async def update_tokens(
        self,
        token_id: str,
        access_token: str,
        refresh_token: str,
        expiry: datetime
    ) -> ProviderToken:
        """Update existing provider tokens"""
        pass


class Contact:
    """Contact domain model"""
    def __init__(
        self,
        id: str,
        user_id: str,
        email: str,
        name: Optional[str],
        company: Optional[str],
        phone: Optional[str],
        custom_fields: Dict[str, Any],
        source: str,
        created_at: datetime,
        updated_at: datetime
    ):
        self.id = id
        self.user_id = user_id
        self.email = email
        self.name = name
        self.company = company
        self.phone = phone
        self.custom_fields = custom_fields
        self.source = source
        self.created_at = created_at
        self.updated_at = updated_at


class ContactRepository(ABC):
    """Abstract repository for contact operations"""

    @abstractmethod
    async def create_contact(
        self,
        user_id: str,
        email: str,
        name: Optional[str],
        company: Optional[str],
        phone: Optional[str],
        custom_fields: Dict[str, Any],
        source: str
    ) -> Contact:
        """Create a new contact"""
        pass

    @abstractmethod
    async def bulk_create_contacts(
        self,
        contacts_data: List[Dict[str, Any]]
    ) -> List[Contact]:
        """Create multiple contacts in bulk"""
        pass

    @abstractmethod
    async def get_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Contact]:
        """Get contacts by user ID with pagination"""
        pass

    @abstractmethod
    async def get_by_user_and_email(
        self,
        user_id: str,
        email: str
    ) -> Optional[Contact]:
        """Get contact by user ID and email"""
        pass

    @abstractmethod
    async def delete_by_id(self, contact_id: str) -> bool:
        """Delete a contact by ID"""
        pass

    @abstractmethod
    async def count_by_user(self, user_id: str) -> int:
        """Count total contacts for a user"""
        pass

    @abstractmethod
    async def get_csv_uploads_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get list of CSV uploads with contact counts for a user"""
        pass

    @abstractmethod
    async def get_contacts_by_source(
        self,
        user_id: str,
        source: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Contact]:
        """Get contacts by user ID and CSV source"""
        pass


class Template:
    """Template domain model"""
    def __init__(
        self,
        id: str,
        user_id: str,
        name: str,
        subject: str,
        body: str,
        variables: List[str],
        is_active: bool,
        created_at: datetime,
        updated_at: datetime
    ):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.subject = subject
        self.body = body
        self.variables = variables
        self.is_active = is_active
        self.created_at = created_at
        self.updated_at = updated_at


class Prompt:
    """AI Prompt domain model"""
    def __init__(
        self,
        id: str,
        user_id: str,
        name: str,
        description: Optional[str],
        prompt_text: str,
        is_default: bool,
        is_active: bool,
        created_at: datetime,
        updated_at: datetime
    ):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.description = description
        self.prompt_text = prompt_text
        self.is_default = is_default
        self.is_active = is_active
        self.created_at = created_at
        self.updated_at = updated_at


class PromptRepository(ABC):
    """Abstract repository for AI prompt operations"""

    @abstractmethod
    async def create_prompt(
        self,
        user_id: str,
        name: str,
        prompt_text: str,
        description: Optional[str] = None,
        is_default: bool = False
    ) -> Prompt:
        """Create a new prompt"""
        pass

    @abstractmethod
    async def get_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Prompt]:
        """Get prompts by user ID with pagination"""
        pass

    @abstractmethod
    async def get_by_id(self, prompt_id: str) -> Optional[Prompt]:
        """Get prompt by ID"""
        pass

    @abstractmethod
    async def get_default_for_user(self, user_id: str) -> Optional[Prompt]:
        """Get user's default prompt"""
        pass

    @abstractmethod
    async def update_prompt(
        self,
        prompt_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        prompt_text: Optional[str] = None,
        is_default: Optional[bool] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Prompt]:
        """Update an existing prompt"""
        pass

    @abstractmethod
    async def set_as_default(self, user_id: str, prompt_id: str) -> Optional[Prompt]:
        """Set a prompt as the user's default (unsets other defaults)"""
        pass

    @abstractmethod
    async def delete_by_id(self, prompt_id: str) -> bool:
        """Delete a prompt by ID"""
        pass

    @abstractmethod
    async def count_by_user(self, user_id: str) -> int:
        """Count total prompts for a user"""
        pass


class TemplateRepository(ABC):
    """Abstract repository for template operations"""

    @abstractmethod
    async def create_template(
        self,
        user_id: str,
        name: str,
        subject: str,
        body: str,
        variables: List[str]
    ) -> Template:
        """Create a new template"""
        pass

    @abstractmethod
    async def get_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Template]:
        """Get templates by user ID with pagination"""
        pass

    @abstractmethod
    async def get_by_id(self, template_id: str) -> Optional[Template]:
        """Get template by ID"""
        pass

    @abstractmethod
    async def update_template(
        self,
        template_id: str,
        name: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        variables: Optional[List[str]] = None,
        is_active: Optional[bool] = None
    ) -> Template:
        """Update an existing template"""
        pass

    @abstractmethod
    async def delete_by_id(self, template_id: str) -> bool:
        """Delete a template by ID"""
        pass

    @abstractmethod
    async def count_by_user(self, user_id: str) -> int:
        """Count total templates for a user"""
        pass


class EmailLog:
    """Email log domain model"""
    def __init__(
        self,
        id: str,
        user_id: str,
        campaign_id: Optional[str],
        contact_id: str,
        template_id: str,
        to_email: str,
        subject: str,
        body: str,
        status: str,
        error_message: Optional[str],
        sent_at: Optional[datetime],
        created_at: datetime,
        gmail_message_id: Optional[str] = None,
        gmail_thread_id: Optional[str] = None,
        reply_count: int = 0
    ):
        self.id = id
        self.user_id = user_id
        self.campaign_id = campaign_id
        self.contact_id = contact_id
        self.template_id = template_id
        self.to_email = to_email
        self.subject = subject
        self.body = body
        self.status = status
        self.error_message = error_message
        self.sent_at = sent_at
        self.created_at = created_at
        self.gmail_message_id = gmail_message_id
        self.gmail_thread_id = gmail_thread_id
        self.reply_count = reply_count


class EmailLogRepository(ABC):
    """Abstract repository for email log operations"""

    @abstractmethod
    async def create_log(
        self,
        user_id: str,
        campaign_id: Optional[str],
        contact_id: str,
        template_id: str,
        to_email: str,
        subject: str,
        body: str,
        status: str,
        error_message: Optional[str] = None,
        sent_at: Optional[datetime] = None
    ) -> EmailLog:
        """Create a new email log entry"""
        pass

    @abstractmethod
    async def get_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[EmailLog]:
        """Get email logs by user ID with pagination"""
        pass

    @abstractmethod
    async def get_by_campaign(
        self,
        campaign_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[EmailLog]:
        """Get email logs by campaign ID"""
        pass

    @abstractmethod
    async def count_by_user(self, user_id: str) -> int:
        """Count total email logs for a user"""
        pass

    @abstractmethod
    async def get_campaign_stats(self, campaign_id: str) -> Dict[str, Any]:
        """Get statistics for a campaign"""
        pass


# Campaign Models
class Campaign(BaseModel):
    """Campaign domain model"""
    id: str
    user_id: str
    name: str
    csv_source: str
    template_id: str
    prompt_id: Optional[str] = None  # AI prompt for auto-replies
    status: str
    total_contacts: int
    processed: int
    sent: int
    failed: int
    trigger_run_id: Optional[str] = None
    error_message: Optional[str] = None
    # Auto-reply settings
    auto_reply_enabled: bool = True
    auto_reply_subject: str = "Re: {{original_subject}}"
    auto_reply_body: str = "Thank you for your reply! We have received your message and will get back to you shortly."
    max_replies_per_thread: int = 5
    replies_count: int = 0
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime


class Conversation(BaseModel):
    """Conversation (email thread) domain model"""
    id: str
    user_id: str
    campaign_id: str
    email_log_id: str
    contact_email: str
    gmail_thread_id: str
    status: str = "active"
    message_count: int = 1
    auto_replies_sent: int = 0
    last_message_at: Optional[datetime] = None
    last_reply_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ConversationMessage(BaseModel):
    """Message in a conversation"""
    id: str
    conversation_id: str
    campaign_id: str
    direction: str  # 'outbound' or 'inbound'
    from_email: str
    to_email: str
    subject: str
    body: str
    gmail_message_id: str
    is_auto_reply: bool = False
    sent_at: datetime
    created_at: datetime


class CampaignRepository(ABC):
    """Abstract repository for campaign operations"""

    @abstractmethod
    async def create_campaign(
        self,
        user_id: str,
        name: str,
        csv_source: str,
        template_id: str,
        total_contacts: int,
        status: str = "queued",
        prompt_id: Optional[str] = None
    ) -> Campaign:
        """Create a new campaign"""
        pass

    @abstractmethod
    async def get_by_id(self, campaign_id: str) -> Optional[Campaign]:
        """Get campaign by ID"""
        pass

    @abstractmethod
    async def get_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Campaign]:
        """Get campaigns by user ID"""
        pass

    @abstractmethod
    async def update_status(
        self,
        campaign_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[Campaign]:
        """Update campaign status"""
        pass

    @abstractmethod
    async def update_progress(
        self,
        campaign_id: str,
        processed: int,
        sent: int,
        failed: int
    ) -> Optional[Campaign]:
        """Update campaign progress"""
        pass

    @abstractmethod
    async def set_trigger_run_id(
        self,
        campaign_id: str,
        trigger_run_id: str
    ) -> Optional[Campaign]:
        """Set Trigger.dev run ID"""
        pass

    @abstractmethod
    async def count_by_user(self, user_id: str) -> int:
        """Count total campaigns for a user"""
        pass

    @abstractmethod
    async def get_by_status(
        self,
        user_id: str,
        status: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Campaign]:
        """Get campaigns by status"""
        pass
