from fastapi import APIRouter, Header, HTTPException
from typing import Optional
from core.templates.models import (
    CreateTemplateRequest,
    UpdateTemplateRequest,
    TemplateResponse,
    TemplateListResponse,
    DeleteTemplateResponse,
    TemplatePreviewRequest,
    TemplatePreviewResponse,
    TemplateItem
)
from core.templates.template_service import TemplateService
from db.repository_factory import get_template_repository
from utils.logger import logger


router = APIRouter(prefix="/templates")


def get_user_id_from_header(x_user_id: Optional[str] = Header(None)) -> str:
    """Extract user ID from header"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User authentication required. Missing X-User-Id header")
    return x_user_id


@router.post("", response_model=TemplateResponse)
async def create_template(
    request: CreateTemplateRequest,
    x_user_id: Optional[str] = Header(None)
):
    """Create a new email template"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        # Validate template
        is_valid, errors = TemplateService.validate_template(request.subject, request.body)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid template: {'; '.join(errors)}")
        
        # Extract variables
        variables = TemplateService.extract_template_variables(request.subject, request.body)
        
        # Create template
        template_repo = await get_template_repository()
        template = await template_repo.create_template(
            user_id=user_id,
            name=request.name,
            subject=request.subject,
            body=request.body,
            variables=variables
        )
        
        template_item = TemplateItem(
            id=template.id,
            name=template.name,
            subject=template.subject,
            body=template.body,
            variables=template.variables,
            is_active=template.is_active,
            created_at=template.created_at,
            updated_at=template.updated_at
        )
        
        return TemplateResponse(
            success=True,
            message="Template created successfully",
            template=template_item
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating template: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    x_user_id: Optional[str] = Header(None),
    page: int = 1,
    page_size: int = 50
):
    """List user's templates"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        template_repo = await get_template_repository()
        
        # Calculate pagination
        skip = (page - 1) * page_size
        
        # Get templates
        templates = await template_repo.get_by_user(user_id, skip=skip, limit=page_size)
        total = await template_repo.count_by_user(user_id)
        
        # Convert to response models
        template_items = [
            TemplateItem(
                id=t.id,
                name=t.name,
                subject=t.subject,
                body=t.body,
                variables=t.variables,
                is_active=t.is_active,
                created_at=t.created_at,
                updated_at=t.updated_at
            )
            for t in templates
        ]
        
        return TemplateListResponse(
            templates=template_items,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing templates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    x_user_id: Optional[str] = Header(None)
):
    """Get a single template by ID"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        template_repo = await get_template_repository()
        template = await template_repo.get_by_id(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Verify ownership
        if template.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        template_item = TemplateItem(
            id=template.id,
            name=template.name,
            subject=template.subject,
            body=template.body,
            variables=template.variables,
            is_active=template.is_active,
            created_at=template.created_at,
            updated_at=template.updated_at
        )
        
        return TemplateResponse(
            success=True,
            message="Template retrieved successfully",
            template=template_item
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    request: UpdateTemplateRequest,
    x_user_id: Optional[str] = Header(None)
):
    """Update an existing template"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        template_repo = await get_template_repository()
        
        # Check if template exists and user owns it
        existing = await template_repo.get_by_id(template_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Template not found")
        if existing.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Validate if subject or body is being updated
        subject = request.subject if request.subject is not None else existing.subject
        body = request.body if request.body is not None else existing.body
        
        is_valid, errors = TemplateService.validate_template(subject, body)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid template: {'; '.join(errors)}")
        
        # Extract variables if subject or body changed
        variables = None
        if request.subject is not None or request.body is not None:
            variables = TemplateService.extract_template_variables(subject, body)
        
        # Update template
        template = await template_repo.update_template(
            template_id=template_id,
            name=request.name,
            subject=request.subject,
            body=request.body,
            variables=variables,
            is_active=request.is_active
        )
        
        template_item = TemplateItem(
            id=template.id,
            name=template.name,
            subject=template.subject,
            body=template.body,
            variables=template.variables,
            is_active=template.is_active,
            created_at=template.created_at,
            updated_at=template.updated_at
        )
        
        return TemplateResponse(
            success=True,
            message="Template updated successfully",
            template=template_item
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{template_id}", response_model=DeleteTemplateResponse)
async def delete_template(
    template_id: str,
    x_user_id: Optional[str] = Header(None)
):
    """Delete a template"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        template_repo = await get_template_repository()
        
        # Check if template exists and user owns it
        existing = await template_repo.get_by_id(template_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Template not found")
        if existing.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete template
        success = await template_repo.delete_by_id(template_id)
        
        if success:
            return DeleteTemplateResponse(
                success=True,
                message="Template deleted successfully"
            )
        else:
            raise HTTPException(status_code=404, detail="Template not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{template_id}/preview", response_model=TemplatePreviewResponse)
async def preview_template(
    template_id: str,
    request: TemplatePreviewRequest,
    x_user_id: Optional[str] = Header(None)
):
    """Preview template with sample data"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        template_repo = await get_template_repository()
        template = await template_repo.get_by_id(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        if template.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Generate preview
        preview = TemplateService.preview_template(
            template.subject,
            template.body,
            request.sample_data
        )
        
        return TemplatePreviewResponse(
            subject=preview["subject"],
            body=preview["body"],
            variables=template.variables
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing template: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

