from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ContactItem(BaseModel):
    """Single contact item"""
    id: str
    email: str
    name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    source: str
    created_at: datetime
    updated_at: datetime


class ContactUploadResponse(BaseModel):
    """Response for contact upload"""
    success: bool
    total_rows: int
    imported: int
    duplicates: int
    invalid: int
    message: str
    contacts: List[ContactItem] = Field(default_factory=list)


class ContactListResponse(BaseModel):
    """Response for listing contacts"""
    contacts: List[ContactItem]
    total: int
    page: int
    page_size: int


class ContactStatsResponse(BaseModel):
    """Response for contact statistics"""
    total_contacts: int
    sources: Dict[str, int] = Field(default_factory=dict)


class DeleteContactResponse(BaseModel):
    """Response for contact deletion"""
    success: bool
    message: str

