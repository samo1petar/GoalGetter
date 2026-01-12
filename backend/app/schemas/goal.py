"""
Pydantic schemas for Goal-related requests and responses.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class MilestoneSchema(BaseModel):
    """Schema for a milestone within a goal."""
    title: str
    description: Optional[str] = None
    target_date: Optional[datetime] = None
    completed: bool = False
    completed_at: Optional[datetime] = None


class GoalMetadataSchema(BaseModel):
    """Schema for goal metadata."""
    deadline: Optional[datetime] = None
    milestones: List[MilestoneSchema] = []
    tags: List[str] = []


class GoalBase(BaseModel):
    """Base goal schema with common fields."""
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(default="", max_length=50000)


class GoalCreate(GoalBase):
    """Schema for creating a new goal."""
    phase: str = Field(default="draft", pattern="^(draft|active|completed|archived)$")
    template_type: str = Field(default="custom", pattern="^(smart|okr|custom)$")
    deadline: Optional[datetime] = None
    milestones: Optional[List[MilestoneSchema]] = None
    tags: Optional[List[str]] = None


class GoalUpdate(BaseModel):
    """Schema for updating an existing goal."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, max_length=50000)
    phase: Optional[str] = Field(None, pattern="^(draft|active|completed|archived)$")
    deadline: Optional[datetime] = None
    milestones: Optional[List[MilestoneSchema]] = None
    tags: Optional[List[str]] = None


class GoalPhaseUpdate(BaseModel):
    """Schema for updating goal phase."""
    phase: str = Field(..., pattern="^(draft|active|completed|archived)$")


class GoalMetadataResponse(BaseModel):
    """Schema for goal metadata in response."""
    deadline: Optional[str] = None
    milestones: List[Dict[str, Any]] = []
    tags: List[str] = []


class GoalResponse(GoalBase):
    """Schema for goal response."""
    id: str
    user_id: str
    phase: str
    template_type: str
    created_at: str
    updated_at: str
    metadata: GoalMetadataResponse

    class Config:
        from_attributes = True


class GoalListResponse(BaseModel):
    """Schema for paginated goal list response."""
    goals: List[GoalResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class GoalFromTemplateCreate(BaseModel):
    """Schema for creating a goal from a template."""
    template_type: str = Field(..., pattern="^(smart|okr|custom)$")
    title: str = Field(..., min_length=1, max_length=200)
    field_values: Optional[Dict[str, str]] = None
    deadline: Optional[datetime] = None
    tags: Optional[List[str]] = None


class TemplateFieldSchema(BaseModel):
    """Schema for a template field."""
    name: str
    label: str
    type: str
    required: bool = False


class GoalTemplateResponse(BaseModel):
    """Schema for goal template response."""
    type: str
    name: str
    description: str
    template_content: str
    fields: List[TemplateFieldSchema]
    is_active: bool = True


class GoalTemplateListResponse(BaseModel):
    """Schema for list of templates."""
    templates: List[GoalTemplateResponse]


class GoalExportResponse(BaseModel):
    """Schema for goal export response."""
    filename: str
    content_type: str = "application/pdf"
    message: str = "PDF generated successfully"
