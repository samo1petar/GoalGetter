"""
Context API routes for Session Context Memory.
Provides endpoints for context extraction, welcome summaries, and context history.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel, Field
from typing import List, Optional

from app.core.database import get_database
from app.core.security import get_current_active_user
from app.services.context_service import get_context_service, ContextService
from app.services.welcome_service import get_welcome_service, WelcomeService

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limiter for context endpoints
limiter = Limiter(key_func=get_remote_address)


# Pydantic schemas for context endpoints

class ContextPointResponse(BaseModel):
    """Schema for a context point in API responses."""
    type: str
    content: str
    related_goal_id: Optional[str] = None
    timestamp: str


class SessionContextResponse(BaseModel):
    """Schema for session context in API responses."""
    id: str
    user_id: str
    session_id: str
    created_at: str
    ended_at: Optional[str] = None
    context_points: List[ContextPointResponse]
    message_count: int
    goals_created: int
    goals_updated: int
    goals_completed: int
    is_summary: bool
    summarized_session_ids: Optional[List[str]] = None


class WelcomeSummaryResponse(BaseModel):
    """Schema for welcome summary response."""
    summary: Optional[str] = None
    has_context: bool
    context_points_count: int
    sessions_count: int
    error: Optional[str] = None


class ContextHistoryResponse(BaseModel):
    """Schema for context history response."""
    contexts: List[SessionContextResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class ContextStatsResponse(BaseModel):
    """Schema for context statistics response."""
    total_sessions: int
    total_summaries: int
    total_messages_processed: int
    total_goals_created: int
    total_goals_updated: int
    total_goals_completed: int
    total_context_points: int
    is_first_time: bool


class ExtractContextRequest(BaseModel):
    """Schema for manual context extraction request."""
    session_id: Optional[str] = None


class ExtractContextResponse(BaseModel):
    """Schema for context extraction response."""
    success: bool
    context_id: Optional[str] = None
    message: str


class DeleteContextResponse(BaseModel):
    """Schema for delete context response."""
    success: bool
    deleted_count: int
    message: str


# Endpoints

@router.get("/summary", response_model=WelcomeSummaryResponse)
@limiter.limit("10/minute")
async def get_welcome_summary(
    request: Request,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Get welcome summary for the current user.

    Returns a personalized welcome message based on the user's previous session context.
    First-time users will receive a response indicating no context is available.

    Rate limit: 10 requests per minute.
    """
    welcome_service = get_welcome_service(db)
    result = await welcome_service.generate_welcome_summary(current_user["id"])

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate welcome summary",
        )

    return WelcomeSummaryResponse(**result)


@router.get("/stats", response_model=ContextStatsResponse)
@limiter.limit("30/minute")
async def get_context_stats(
    request: Request,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Get context statistics for the current user.

    Returns quick stats about user's session history without generating an AI summary.

    Rate limit: 30 requests per minute.
    """
    welcome_service = get_welcome_service(db)
    result = await welcome_service.get_quick_context_summary(current_user["id"])
    return ContextStatsResponse(**result)


@router.post("/extract", response_model=ExtractContextResponse)
@limiter.limit("5/minute")
async def extract_context(
    request: Request,
    body: ExtractContextRequest = ExtractContextRequest(),
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Manually trigger context extraction for the current user.

    This endpoint extracts context from recent conversation history.
    Normally context is extracted automatically on logout or session end.

    Rate limit: 5 requests per minute.
    """
    context_service = get_context_service(db)

    # Generate session ID if not provided
    session_id = body.session_id
    if not session_id:
        session_id = await context_service.generate_session_id()

    # Extract and save context
    context_id = await context_service.extract_and_save_context(
        user_id=current_user["id"],
        session_id=session_id,
    )

    if context_id:
        return ExtractContextResponse(
            success=True,
            context_id=context_id,
            message="Context extracted and saved successfully",
        )
    else:
        return ExtractContextResponse(
            success=False,
            context_id=None,
            message="No meaningful context to extract from recent conversations",
        )


@router.get("/history", response_model=ContextHistoryResponse)
@limiter.limit("30/minute")
async def get_context_history(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Get paginated context history for the current user.

    Returns all session contexts (both individual sessions and summaries).

    Rate limit: 30 requests per minute.
    """
    context_service = get_context_service(db)
    result = await context_service.get_context_history(
        user_id=current_user["id"],
        page=page,
        page_size=page_size,
    )
    return ContextHistoryResponse(**result)


@router.delete("/history", response_model=DeleteContextResponse)
@limiter.limit("5/minute")
async def delete_context_history(
    request: Request,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Delete all context history for the current user.

    This action is irreversible and removes all session context data.
    Use this for GDPR compliance or user privacy requests.

    Rate limit: 5 requests per minute.
    """
    context_service = get_context_service(db)
    deleted_count = await context_service.delete_user_context(current_user["id"])

    return DeleteContextResponse(
        success=True,
        deleted_count=deleted_count,
        message=f"Successfully deleted {deleted_count} context records",
    )
