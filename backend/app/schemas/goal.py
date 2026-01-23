"""
Pydantic schemas for Goal-related requests and responses.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class MilestoneSchema(BaseModel):
    """Schema for a milestone within a goal."""
    # SECURITY: Length limits prevent resource exhaustion and excessive API costs
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    target_date: Optional[datetime] = None
    completed: bool = False
    completed_at: Optional[datetime] = None


class GoalMetadataSchema(BaseModel):
    """Schema for goal metadata."""
    deadline: Optional[datetime] = None
    milestones: List[MilestoneSchema] = []
    tags: List[str] = []


class GoalBase(BaseModel):
    """
    Base goal schema with common fields.

    SECURITY: Length limits prevent resource exhaustion, excessive storage costs,
    and help mitigate prompt injection attacks by limiting injection surface area.
    """
    title: str = Field(..., min_length=1, max_length=200)
    # SECURITY: 50KB limit prevents excessive API costs and storage abuse
    content: str = Field(default="", max_length=50000)


class GoalCreate(GoalBase):
    """Schema for creating a new goal."""
    phase: str = Field(default="draft", pattern="^(draft|active|completed|archived)$")
    template_type: str = Field(default="custom", pattern="^(smart|okr|custom)$")
    deadline: Optional[datetime] = None
    # SECURITY: Limit number of milestones to prevent abuse
    milestones: Optional[List[MilestoneSchema]] = Field(None, max_length=50)
    # SECURITY: Limit tags count and length
    tags: Optional[List[str]] = Field(None, max_length=20)

    @field_validator('tags')
    @classmethod
    def validate_tag_lengths(cls, v):
        """Validate individual tag lengths."""
        if v:
            for tag in v:
                if len(tag) > 50:
                    raise ValueError('Each tag must be 50 characters or less')
        return v


class GoalUpdate(BaseModel):
    """Schema for updating an existing goal."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    # SECURITY: 50KB limit prevents excessive API costs and storage abuse
    content: Optional[str] = Field(None, max_length=50000)
    phase: Optional[str] = Field(None, pattern="^(draft|active|completed|archived)$")
    deadline: Optional[datetime] = None
    # SECURITY: Limit number of milestones to prevent abuse
    milestones: Optional[List[MilestoneSchema]] = Field(None, max_length=50)
    # SECURITY: Limit tags count and length
    tags: Optional[List[str]] = Field(None, max_length=20)

    @field_validator('tags')
    @classmethod
    def validate_tag_lengths(cls, v):
        """Validate individual tag lengths."""
        if v:
            for tag in v:
                if len(tag) > 50:
                    raise ValueError('Each tag must be 50 characters or less')
        return v


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
