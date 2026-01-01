from fastapi import APIRouter, Header, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timedelta
import os
import json
import httpx
from db.repository_factory import get_prompt_repository
from db.mongodb.calendar_repository import MongoCalendarRepository
from integrations.calcom_client import CalComClient
from utils.logger import logger
from config import settings


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


class TestPromptMessage(BaseModel):
    """Single message in test conversation"""
    role: str  # 'user' or 'assistant'
    content: str


class TestPromptRequest(BaseModel):
    """Request to test a prompt with the AI"""
    prompt_text: str  # The prompt to test
    user_message: str  # The simulated user (contact) message
    conversation_history: List[TestPromptMessage] = []  # Optional previous messages
    cal_tools_enabled: bool = False  # Whether to enable calendar tools


class TestPromptResponse(BaseModel):
    """Response from testing a prompt"""
    success: bool
    ai_response: Optional[str] = None
    error: Optional[str] = None
    booking_url: Optional[str] = None
    booking_id: Optional[str] = None


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


@router.post("/test", response_model=TestPromptResponse)
async def test_prompt(
    request: TestPromptRequest,
    x_user_id: Optional[str] = Header(None)
):
    """
    Test a prompt by chatting with the AI directly.
    Simulates how the AI would respond to an email using the given prompt.
    Supports calendar tools if enabled.
    """
    user_id = get_user_id_from_header(x_user_id)

    try:
        # Get API key from settings or environment (for backward compatibility)
        api_key = (
            settings.google_generative_ai_api_key or
            os.getenv("GOOGLE_GENERATIVE_AI_API_KEY") or
            os.getenv("GOOGLE_GEMINI_API_KEY") or
            os.getenv("GOOGLE_API_KEY")
        )
        
        if not api_key:
            return TestPromptResponse(
                success=False,
                error="AI API key not configured. Please set GOOGLE_GENERATIVE_AI_API_KEY in your .env file or environment variables."
            )

        # Build conversation history for context
        history_text = ""
        for msg in request.conversation_history[-5:]:  # Last 5 messages
            direction = "INBOUND" if msg.role == "user" else "OUTBOUND"
            history_text += f"[{direction}]: {msg.content[:300]}\n\n"

        # Build the system prompt
        current_date = datetime.utcnow()
        current_date_str = current_date.strftime("%Y-%m-%d")
        current_datetime_str = current_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        calendar_instructions = ""
        if request.cal_tools_enabled:
            calendar_instructions = f"""

IMPORTANT - CURRENT DATE/TIME: {current_datetime_str}
When booking meetings, ONLY use times from the getCalendarAvailability tool results.
These are the ONLY valid future time slots. Do NOT make up times.
Remember: When they agree to meet, book immediately using contactEmail and contactName above."""
        
        system_prompt = f"""{request.prompt_text}

CONTACT INFORMATION (USE THESE - DO NOT ASK):
- Contact Email: test@example.com
- Contact Name: Test User

Today's Date: {current_date_str}

Context: Testing prompt with simulated email conversation

Previous conversation:
{history_text or 'No previous messages.'}

Latest email from Test User (test@example.com):
Subject: Test Conversation
Message: {request.user_message}{calendar_instructions}"""

        # Define tools if calendar is enabled
        tools = None
        if request.cal_tools_enabled:
            tools = [{
                "function_declarations": [
                    {
                        "name": "getCalendarAvailability",
                        "description": "Get calendar availability for a specified number of days ahead. Use this when the contact asks about available times.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "daysAhead": {
                                    "type": "integer",
                                    "description": "Number of days to check ahead (default: 14)"
                                }
                            }
                        }
                    },
                    {
                        "name": "bookMeeting",
                        "description": "Book a meeting slot when the contact agrees to meet. Use contactEmail and contactName from context.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "startTime": {
                                    "type": "string",
                                    "description": "Start time in ISO format"
                                },
                                "endTime": {
                                    "type": "string",
                                    "description": "End time in ISO format"
                                },
                                "attendeeEmail": {
                                    "type": "string",
                                    "description": "Email address of the attendee"
                                },
                                "attendeeName": {
                                    "type": "string",
                                    "description": "Name of the attendee"
                                },
                                "notes": {
                                    "type": "string",
                                    "description": "Optional notes about the meeting"
                                }
                            },
                            "required": ["startTime", "endTime", "attendeeEmail", "attendeeName"]
                        }
                    }
                ]
            }]

        # Build request payload
        gemini_payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{system_prompt}\n\nGenerate a professional reply to the latest email."}]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": 1500,
                "temperature": 0.7
            }
        }
        
        if tools:
            gemini_payload["tools"] = tools

        booking_url = None
        booking_id = None
        max_iterations = 3

        async with httpx.AsyncClient() as client:
            for iteration in range(max_iterations):
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}",
                    json=gemini_payload,
                    timeout=60.0
                )

                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"Gemini API error: {response.status_code} - {error_text}")
                    return TestPromptResponse(
                        success=False,
                        error=f"AI API error: {response.status_code}"
                    )

                data = response.json()
                candidates = data.get("candidates", [])
                
                if not candidates:
                    return TestPromptResponse(
                        success=False,
                        error="No response from AI"
                    )
                
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                
                if not parts:
                    return TestPromptResponse(
                        success=False,
                        error="Empty response from AI"
                    )
                
                # Check for function calls
                function_call = parts[0].get("functionCall")
                
                if function_call and request.cal_tools_enabled:
                    # Execute the function
                    func_name = function_call.get("name")
                    func_args = function_call.get("args", {})
                    
                    logger.info(f"AI called function: {func_name} with args: {func_args}")
                    
                    function_result = await execute_calendar_function(user_id, func_name, func_args)
                    
                    # Check if booking was successful
                    if func_name == "bookMeeting" and function_result.get("success"):
                        booking_url = function_result.get("booking_url")
                        booking_id = function_result.get("booking_id")
                    
                    # Add function result to conversation and continue
                    gemini_payload["contents"].append({
                        "role": "model",
                        "parts": [{"functionCall": function_call}]
                    })
                    gemini_payload["contents"].append({
                        "role": "user",
                        "parts": [{"functionResponse": {
                            "name": func_name,
                            "response": function_result
                        }}]
                    })
                    
                    # Continue to next iteration to get final response
                    continue
                
                # Got a text response
                ai_response = parts[0].get("text", "")
                
                return TestPromptResponse(
                    success=True,
                    ai_response=ai_response,
                    booking_url=booking_url,
                    booking_id=booking_id
                )
            
            # Max iterations reached
            return TestPromptResponse(
                success=False,
                error="AI took too many steps to respond"
            )

    except httpx.TimeoutException:
        return TestPromptResponse(
            success=False,
            error="AI request timed out. Please try again."
        )
    except Exception as e:
        logger.error(f"Error testing prompt: {str(e)}")
        return TestPromptResponse(
            success=False,
            error=str(e)
        )


async def execute_calendar_function(user_id: str, func_name: str, args: dict) -> dict:
    """Execute a calendar function and return the result"""
    try:
        calendar_repo = MongoCalendarRepository()
        token = await calendar_repo.get_by_user(user_id, "cal.com")
        
        if not token:
            return {"error": "Calendar not connected", "connected": False}
        
        client = CalComClient(token["api_key"])
        
        if func_name == "getCalendarAvailability":
            days_ahead = args.get("daysAhead", 30)  # Default to 30 days
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=days_ahead)
            
            event_type_id = token.get("event_type_id")
            if not event_type_id:
                event_types = await client.get_event_types()
                if event_types:
                    event_type_id = event_types[0].get("id")
            
            slots = await client.get_availability(
                event_type_id=event_type_id,
                start_date=start_date,
                end_date=end_date,
                timezone="UTC"
            )
            
            # Group slots by date to show variety across days
            formatted_slots = []
            slots_by_date = {}
            for slot in slots:
                start_raw = slot.get("start") or slot.get("time")
                if start_raw:
                    date_key = start_raw[:10]  # YYYY-MM-DD
                    if date_key not in slots_by_date:
                        slots_by_date[date_key] = []
                    slots_by_date[date_key].append({
                        "start": start_raw,
                        "end": slot.get("end") or slot.get("endTime"),
                    })
            
            # Take up to 3 slots per day, max 20 total slots across multiple days
            for date_key in sorted(slots_by_date.keys())[:10]:  # Up to 10 different days
                for slot in slots_by_date[date_key][:3]:  # Up to 3 slots per day
                    formatted_slots.append(slot)
                    if len(formatted_slots) >= 20:
                        break
                if len(formatted_slots) >= 20:
                    break
            
            username = token.get("username")
            event_slug = token.get("event_type_slug")
            
            return {
                "connected": True,
                "available_slots": formatted_slots,
                "booking_link": f"https://cal.com/{username}/{event_slug}" if event_slug else None,
                "event_type_name": token.get("event_type_name")
            }
        
        elif func_name == "bookMeeting":
            event_type_id = token.get("event_type_id")
            if not event_type_id:
                event_types = await client.get_event_types()
                if event_types:
                    event_type_id = event_types[0].get("id")
            
            start_time = datetime.fromisoformat(args["startTime"].replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(args["endTime"].replace("Z", "+00:00"))
            
            result = await client.create_booking(
                event_type_id=event_type_id,
                start_time=start_time,
                end_time=end_time,
                attendee_email=args["attendeeEmail"],
                attendee_name=args["attendeeName"],
                notes=args.get("notes"),
                timezone="UTC"
            )
            
            booking_data = result.get("data", result)
            
            return {
                "success": True,
                "booking_id": str(booking_data.get("id")) if booking_data.get("id") else None,
                "booking_url": booking_data.get("url") or booking_data.get("bookingUrl"),
                "message": "Meeting booked successfully!"
            }
        
        return {"error": f"Unknown function: {func_name}"}
        
    except Exception as e:
        logger.error(f"Error executing calendar function: {str(e)}")
        return {"error": str(e)}

