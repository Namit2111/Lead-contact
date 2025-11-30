from pydantic import BaseModel, Field
from pydantic_core import core_schema
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId for Pydantic models"""

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return core_schema.union_schema([
            core_schema.is_instance_schema(ObjectId),
            core_schema.no_info_plain_validator_function(cls.validate),
        ])

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        raise ValueError("Invalid ObjectId")

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        return {"type": "string"}


class UserDocument(BaseModel):
    """MongoDB document schema for users collection"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    email: str
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ProviderTokenDocument(BaseModel):
    """MongoDB document schema for provider_tokens collection"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    provider: str
    access_token: str
    refresh_token: str
    expiry: datetime
    scope: List[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ContactDocument(BaseModel):
    """MongoDB document schema for contacts collection"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    email: str
    name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    source: str  # CSV filename
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class TemplateDocument(BaseModel):
    """MongoDB document schema for templates collection"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    name: str
    subject: str
    body: str
    variables: List[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class PromptDocument(BaseModel):
    """MongoDB document schema for AI prompts collection"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    name: str
    description: Optional[str] = None
    prompt_text: str
    is_default: bool = False
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class CampaignDocument(BaseModel):
    """MongoDB document schema for campaigns collection"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    name: str
    csv_source: str
    template_id: PyObjectId
    prompt_id: Optional[PyObjectId] = None  # AI prompt for auto-replies (None = system default)
    status: str  # 'queued', 'running', 'paused', 'completed', 'failed', 'cancelled'
    total_contacts: int = 0
    processed: int = 0
    sent: int = 0
    failed: int = 0
    trigger_run_id: Optional[str] = None  # Trigger.dev run ID for tracking
    error_message: Optional[str] = None
    # Auto-reply settings (enabled by default)
    auto_reply_enabled: bool = True
    auto_reply_subject: str = "Re: {{original_subject}}"
    auto_reply_body: str = "Thank you for your reply! We have received your message and will get back to you shortly."
    max_replies_per_thread: int = 5
    replies_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class EmailLogDocument(BaseModel):
    """MongoDB document schema for email_logs collection"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    campaign_id: Optional[str] = None  # Group emails from same campaign
    contact_id: PyObjectId
    template_id: PyObjectId
    to_email: str
    subject: str
    body: str
    status: str  # 'sent', 'failed', 'pending'
    gmail_message_id: Optional[str] = None  # Gmail's message ID for tracking
    gmail_thread_id: Optional[str] = None  # Gmail's thread ID for reply detection
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    reply_count: int = 0  # How many auto-replies sent in this thread
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ConversationDocument(BaseModel):
    """MongoDB document schema for conversations collection (email threads)"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    campaign_id: str
    email_log_id: str  # Reference to original sent email
    contact_email: str
    gmail_thread_id: str  # Gmail's thread ID
    status: str = "active"  # 'active', 'paused', 'closed'
    message_count: int = 1  # Total messages in thread
    auto_replies_sent: int = 0
    last_message_at: Optional[datetime] = None
    last_reply_at: Optional[datetime] = None  # Last time they replied
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ConversationMessageDocument(BaseModel):
    """MongoDB document schema for conversation messages"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    conversation_id: PyObjectId
    campaign_id: str
    direction: str  # 'outbound' (us to them) or 'inbound' (them to us)
    from_email: str
    to_email: str
    subject: str
    body: str
    gmail_message_id: str
    is_auto_reply: bool = False
    sent_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
