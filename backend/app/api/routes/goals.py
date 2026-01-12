"""
Goals API endpoints.
Handles CRUD operations for user goals including create, read, update, delete,
and PDF export functionality.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
import math

from app.core.database import get_database
from app.core.security import get_current_active_user
from app.core.config import settings
from app.services.goal_service import GoalService
from app.services.pdf_service import pdf_service
from app.schemas.goal import (
    GoalCreate,
    GoalUpdate,
    GoalPhaseUpdate,
    GoalResponse,
    GoalListResponse,
    GoalFromTemplateCreate,
    GoalExportResponse,
)

router = APIRouter()


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    goal_data: GoalCreate,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Create a new goal.

    - **title**: Goal title (required)
    - **content**: Goal content in markdown format
    - **phase**: Goal phase (draft, active, completed, archived)
    - **template_type**: Template type (smart, okr, custom)
    - **deadline**: Optional deadline date
    - **milestones**: Optional list of milestones
    - **tags**: Optional list of tags

    Returns the created goal.
    """
    goal_service = GoalService(db)
    goal = await goal_service.create_goal(
        user_id=current_user["id"],
        goal_data=goal_data,
    )
    return goal


@router.get("", response_model=GoalListResponse)
async def list_goals(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    phase: Optional[str] = Query(
        default=None,
        pattern="^(draft|active|completed|archived)$",
        description="Filter by phase"
    ),
    template_type: Optional[str] = Query(
        default=None,
        pattern="^(smart|okr|custom)$",
        description="Filter by template type"
    ),
    tags: Optional[str] = Query(
        default=None,
        description="Filter by tags (comma-separated)"
    ),
    search: Optional[str] = Query(
        default=None,
        description="Search in title and content"
    ),
    sort_by: str = Query(
        default="created_at",
        pattern="^(created_at|updated_at|title)$",
        description="Sort field"
    ),
    sort_order: str = Query(
        default="desc",
        pattern="^(asc|desc)$",
        description="Sort order"
    ),
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    List all goals for the current user.

    Supports pagination, filtering, searching, and sorting.

    - **page**: Page number (default: 1)
    - **page_size**: Number of items per page (default: 20, max: 100)
    - **phase**: Filter by goal phase
    - **template_type**: Filter by template type
    - **tags**: Filter by tags (comma-separated)
    - **search**: Search in title and content
    - **sort_by**: Sort by field (created_at, updated_at, title)
    - **sort_order**: Sort order (asc, desc)

    Returns paginated list of goals.
    """
    goal_service = GoalService(db)

    # Parse tags if provided
    tags_list = None
    if tags:
        tags_list = [t.strip() for t in tags.split(",") if t.strip()]

    goals, total = await goal_service.get_user_goals(
        user_id=current_user["id"],
        page=page,
        page_size=page_size,
        phase=phase,
        template_type=template_type,
        tags=tags_list,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return GoalListResponse(
        goals=goals,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/statistics")
async def get_goal_statistics(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Get goal statistics for the current user.

    Returns count of goals by phase and total count.
    """
    goal_service = GoalService(db)
    stats = await goal_service.get_goal_statistics(user_id=current_user["id"])
    return stats


@router.post("/from-template", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal_from_template(
    template_data: GoalFromTemplateCreate,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Create a new goal from a template.

    - **template_type**: Template type (smart, okr, custom) (required)
    - **title**: Goal title (required)
    - **field_values**: Optional dict of field values to fill in template
    - **deadline**: Optional deadline date
    - **tags**: Optional list of tags

    Returns the created goal pre-filled with template content.
    """
    goal_service = GoalService(db)
    goal = await goal_service.create_goal_from_template(
        user_id=current_user["id"],
        template_data=template_data,
    )
    return goal


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Get a specific goal by ID.

    - **goal_id**: Goal ID (required)

    Returns the goal if it belongs to the current user.
    """
    goal_service = GoalService(db)
    goal = await goal_service.get_goal_by_id(
        goal_id=goal_id,
        user_id=current_user["id"],
    )
    return goal


@router.put("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: str,
    goal_data: GoalUpdate,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Update an existing goal.

    - **goal_id**: Goal ID (required)
    - **title**: New title (optional)
    - **content**: New content (optional)
    - **phase**: New phase (optional)
    - **deadline**: New deadline (optional)
    - **milestones**: New milestones (optional)
    - **tags**: New tags (optional)

    Returns the updated goal.
    """
    goal_service = GoalService(db)
    goal = await goal_service.update_goal(
        goal_id=goal_id,
        user_id=current_user["id"],
        goal_data=goal_data,
    )
    return goal


@router.patch("/{goal_id}/phase", response_model=GoalResponse)
async def update_goal_phase(
    goal_id: str,
    phase_data: GoalPhaseUpdate,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Update a goal's phase.

    - **goal_id**: Goal ID (required)
    - **phase**: New phase (draft, active, completed, archived)

    Returns the updated goal.
    """
    goal_service = GoalService(db)
    goal = await goal_service.update_goal_phase(
        goal_id=goal_id,
        user_id=current_user["id"],
        phase=phase_data.phase,
    )
    return goal


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Delete a goal.

    - **goal_id**: Goal ID (required)

    Returns 204 No Content on success.
    """
    goal_service = GoalService(db)
    await goal_service.delete_goal(
        goal_id=goal_id,
        user_id=current_user["id"],
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{goal_id}/export")
async def export_goal_as_pdf(
    goal_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Export a goal as a PDF document.

    - **goal_id**: Goal ID (required)

    Returns the PDF file as a downloadable attachment.
    """
    # Check if PDF export is enabled
    if not settings.ENABLE_PDF_EXPORT:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF export is not enabled"
        )

    # Get the goal
    goal_service = GoalService(db)
    goal = await goal_service.get_goal_by_id(
        goal_id=goal_id,
        user_id=current_user["id"],
    )

    # Generate PDF
    try:
        pdf_bytes = pdf_service.generate_goal_pdf(
            goal=goal,
            user_name=current_user.get("name"),
        )
        filename = pdf_service.get_filename_for_goal(goal)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}"
        )

    # Return PDF as downloadable file
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        }
    )
