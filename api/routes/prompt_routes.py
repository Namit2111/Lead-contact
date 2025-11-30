from fastapi import APIRouter, Header, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from db.repository_factory import get_prompt_repository
from utils.logger import logger


router = APIRouter(prefix="/prompts")


# System default prompt - used when no custom prompt is selected
SYSTEM_DEFAULT_PROMPT = """You are a professional sales representative. Your goal is to engage with prospects, understand their needs, and guide conversations toward scheduling meetings.

Context about this conversation will be provided below.

Instructions:
1. ALWAYS respond to every email - your job is to try and keep the conversation going
2. Read the conversation context carefully and respond appropriately
3. Be friendly, professional, and consultative
4. Your primary objective is to schedule a meeting when appropriate
5. Keep replies concise but compelling (3-5 sentences typically)
6. Address their specific questions or concerns
7. If they seem uninterested, acknowledge their position but offer value
8. Never give up - always find a way to continue the conversation

Reply:"""


# Request/Response Models
class CreatePromptRequest(BaseModel):
    """Request to create a new prompt"""
    name: str
    prompt_text: str
    description: Optional[str] = None
    is_default: bool = False


class UpdatePromptRequest(BaseModel):
    """Request to update a prompt"""
    name: Optional[str] = None
    prompt_text: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None


class PromptItem(BaseModel):
    """Single prompt item"""
    id: str
    name: str
    description: Optional[str]
    prompt_text: str
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PromptListResponse(BaseModel):
    """Response with list of prompts"""
    prompts: List[PromptItem]
    total: int
    page: int
    page_size: int


class PromptResponse(BaseModel):
    """Response with single prompt"""
    prompt: PromptItem


class DeletePromptResponse(BaseModel):
    """Response for delete operation"""
    success: bool
    message: str


class SystemDefaultResponse(BaseModel):
    """Response with system default prompt"""
    prompt_text: str
    name: str
    description: str


def get_user_id_from_header(x_user_id: Optional[str] = Header(None)) -> str:
    """Extract user ID from header"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User authentication required. Missing X-User-Id header")
    return x_user_id


@router.get("/system-default", response_model=SystemDefaultResponse)
async def get_system_default_prompt():
    """Get the system default prompt (for reference)"""
    return SystemDefaultResponse(
        prompt_text=SYSTEM_DEFAULT_PROMPT,
        name="System Default",
        description="The built-in default prompt used when no custom prompt is selected"
    )


@router.post("", response_model=PromptResponse)
async def create_prompt(
    request: CreatePromptRequest,
    x_user_id: Optional[str] = Header(None)
):
    """Create a new AI prompt"""
    user_id = get_user_id_from_header(x_user_id)

    try:
        prompt_repo = await get_prompt_repository()

        prompt = await prompt_repo.create_prompt(
            user_id=user_id,
            name=request.name,
            prompt_text=request.prompt_text,
            description=request.description,
            is_default=request.is_default
        )

        return PromptResponse(
            prompt=PromptItem(
                id=prompt.id,
                name=prompt.name,
                description=prompt.description,
                prompt_text=prompt.prompt_text,
                is_default=prompt.is_default,
                is_active=prompt.is_active,
                created_at=prompt.created_at,
                updated_at=prompt.updated_at
            )
        )

    except Exception as e:
        logger.error(f"Error creating prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=PromptListResponse)
async def list_prompts(
    x_user_id: Optional[str] = Header(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """List user's AI prompts"""
    user_id = get_user_id_from_header(x_user_id)

    try:
        prompt_repo = await get_prompt_repository()

        skip = (page - 1) * page_size
        prompts = await prompt_repo.get_by_user(user_id, skip=skip, limit=page_size)
        total = await prompt_repo.count_by_user(user_id)

        prompt_items = [
            PromptItem(
                id=p.id,
                name=p.name,
                description=p.description,
                prompt_text=p.prompt_text,
                is_default=p.is_default,
                is_active=p.is_active,
                created_at=p.created_at,
                updated_at=p.updated_at
            )
            for p in prompts
        ]

        return PromptListResponse(
            prompts=prompt_items,
            total=total,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error(f"Error listing prompts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: str,
    x_user_id: Optional[str] = Header(None)
):
    """Get a specific prompt by ID"""
    user_id = get_user_id_from_header(x_user_id)

    try:
        prompt_repo = await get_prompt_repository()
        prompt = await prompt_repo.get_by_id(prompt_id)

        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found")

        if prompt.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied to prompt")

        return PromptResponse(
            prompt=PromptItem(
                id=prompt.id,
                name=prompt.name,
                description=prompt.description,
                prompt_text=prompt.prompt_text,
                is_default=prompt.is_default,
                is_active=prompt.is_active,
                created_at=prompt.created_at,
                updated_at=prompt.updated_at
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: str,
    request: UpdatePromptRequest,
    x_user_id: Optional[str] = Header(None)
):
    """Update an existing prompt"""
    user_id = get_user_id_from_header(x_user_id)

    try:
        prompt_repo = await get_prompt_repository()

        # Check ownership
        existing = await prompt_repo.get_by_id(prompt_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Prompt not found")
        if existing.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied to prompt")

        prompt = await prompt_repo.update_prompt(
            prompt_id=prompt_id,
            name=request.name,
            description=request.description,
            prompt_text=request.prompt_text,
            is_default=request.is_default
        )

        if not prompt:
            raise HTTPException(status_code=500, detail="Failed to update prompt")

        return PromptResponse(
            prompt=PromptItem(
                id=prompt.id,
                name=prompt.name,
                description=prompt.description,
                prompt_text=prompt.prompt_text,
                is_default=prompt.is_default,
                is_active=prompt.is_active,
                created_at=prompt.created_at,
                updated_at=prompt.updated_at
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{prompt_id}/set-default", response_model=PromptResponse)
async def set_prompt_as_default(
    prompt_id: str,
    x_user_id: Optional[str] = Header(None)
):
    """Set a prompt as the user's default"""
    user_id = get_user_id_from_header(x_user_id)

    try:
        prompt_repo = await get_prompt_repository()

        # Check ownership
        existing = await prompt_repo.get_by_id(prompt_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Prompt not found")
        if existing.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied to prompt")

        prompt = await prompt_repo.set_as_default(user_id, prompt_id)

        if not prompt:
            raise HTTPException(status_code=500, detail="Failed to set default prompt")

        return PromptResponse(
            prompt=PromptItem(
                id=prompt.id,
                name=prompt.name,
                description=prompt.description,
                prompt_text=prompt.prompt_text,
                is_default=prompt.is_default,
                is_active=prompt.is_active,
                created_at=prompt.created_at,
                updated_at=prompt.updated_at
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting default prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{prompt_id}", response_model=DeletePromptResponse)
async def delete_prompt(
    prompt_id: str,
    x_user_id: Optional[str] = Header(None)
):
    """Delete a prompt"""
    user_id = get_user_id_from_header(x_user_id)

    try:
        prompt_repo = await get_prompt_repository()

        # Check ownership
        existing = await prompt_repo.get_by_id(prompt_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Prompt not found")
        if existing.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied to prompt")

        success = await prompt_repo.delete_by_id(prompt_id)

        if success:
            return DeletePromptResponse(
                success=True,
                message="Prompt deleted successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to delete prompt")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

