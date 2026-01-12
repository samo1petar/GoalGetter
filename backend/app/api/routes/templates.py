"""
Templates API endpoints.
Handles retrieval of goal templates for creating structured goals.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.security import get_current_active_user
from app.models.goal import GoalTemplateModel
from app.schemas.goal import (
    GoalTemplateResponse,
    GoalTemplateListResponse,
)

router = APIRouter()


@router.get("", response_model=GoalTemplateListResponse)
async def list_templates(
    current_user: dict = Depends(get_current_active_user),
):
    """
    List all available goal templates.

    Returns a list of all active templates including:
    - SMART Goal template
    - OKR template
    - Custom template

    Each template includes:
    - **type**: Template identifier (smart, okr, custom)
    - **name**: Human-readable template name
    - **description**: Description of the template
    - **template_content**: Default content/structure
    - **fields**: List of fields that can be filled in
    """
    templates = GoalTemplateModel.get_all_templates()
    return GoalTemplateListResponse(templates=templates)


@router.get("/{template_type}", response_model=GoalTemplateResponse)
async def get_template(
    template_type: str,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Get a specific goal template by type.

    - **template_type**: Template type (smart, okr, custom)

    Returns the template details including:
    - **type**: Template identifier
    - **name**: Human-readable template name
    - **description**: Description of the template
    - **template_content**: Default content/structure in markdown format
    - **fields**: List of fields that can be filled in
    - **is_active**: Whether the template is active

    Use this template content when creating a new goal from template
    via POST /api/v1/goals/from-template
    """
    template = GoalTemplateModel.get_template(template_type)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_type}"
        )

    return template


@router.get("/{template_type}/preview")
async def preview_template(
    template_type: str,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Get a preview of what a goal looks like when created from a template.

    - **template_type**: Template type (smart, okr, custom)

    Returns a preview object with:
    - **template**: The template details
    - **example_goal**: Example of how a goal would look

    Useful for displaying to users before they create a goal.
    """
    template = GoalTemplateModel.get_template(template_type)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_type}"
        )

    # Create example based on template type
    examples = {
        "smart": {
            "title": "Example: Learn Python in 3 Months",
            "field_values": {
                "specific": "Complete an intermediate Python course and build 3 projects.",
                "measurable": "Finish 10 modules, score 80%+ on assessments, deploy 3 working projects.",
                "achievable": "I have 2 hours daily and basic programming knowledge.",
                "relevant": "This supports my career goal of becoming a software developer.",
                "time_bound": "Complete by March 31, 2026 with weekly milestones.",
            }
        },
        "okr": {
            "title": "Example: Improve Team Productivity",
            "field_values": {
                "objective": "Transform our team into a high-performing, collaborative unit.",
                "key_result_1": "Reduce meeting time by 30% while maintaining output quality.",
                "key_result_2": "Achieve 90% sprint completion rate.",
                "key_result_3": "Increase team NPS score from 6 to 8.",
                "initiatives": "Implement async communication tools, daily standups, and retrospectives.",
            }
        },
        "custom": {
            "title": "Example: Personal Wellness Goal",
            "field_values": {
                "goal": "Improve overall health and energy levels.",
                "why": "I want to feel more energetic and reduce stress.",
                "action_plan": "Exercise 3x/week, meal prep on Sundays, sleep 8 hours.",
                "timeline": "30-day initial challenge, then quarterly reviews.",
                "obstacles": "Time constraints - solution: morning workouts before work.",
            }
        },
    }

    example = examples.get(template_type, {})

    return {
        "template": template,
        "example": {
            "title": example.get("title", "My Goal"),
            "field_values": example.get("field_values", {}),
        },
        "usage_tips": [
            "Fill in each section thoughtfully for best results",
            "Be specific and measurable where possible",
            "Set realistic timelines and milestones",
            "Review and update your goals regularly",
        ]
    }
