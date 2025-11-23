from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class TemplateItem(BaseModel):
    """Single template item"""
    id: str
    name: str
    subject: str
    body: str
    variables: List[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class CreateTemplateRequest(BaseModel):
    """Request to create a new template"""
    name: str
    subject: str
    body: str


class UpdateTemplateRequest(BaseModel):
    """Request to update a template"""
    name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    is_active: Optional[bool] = None


class TemplateResponse(BaseModel):
    """Response for single template"""
    success: bool
    message: str
    template: Optional[TemplateItem] = None


class TemplateListResponse(BaseModel):
    """Response for listing templates"""
    templates: List[TemplateItem]
    total: int
    page: int
    page_size: int


class DeleteTemplateResponse(BaseModel):
    """Response for template deletion"""
    success: bool
    message: str


class TemplatePreviewRequest(BaseModel):
    """Request to preview template"""
    sample_data: Optional[Dict[str, Any]] = None


class TemplatePreviewResponse(BaseModel):
    """Response for template preview"""
    subject: str
    body: str
    variables: List[str]

