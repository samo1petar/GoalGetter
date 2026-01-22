"""
Goal model for MongoDB.
Represents user goals with phases, templates, and metadata.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from bson import ObjectId


class GoalModel:
    """
    Goal model representing a goal document in the database.
    This is a dict-based model for MongoDB documents.
    """

    VALID_PHASES = ["draft", "active", "completed", "archived"]
    VALID_TEMPLATE_TYPES = ["smart", "okr", "custom"]

    @staticmethod
    def create_goal_document(
        user_id: str,
        title: str,
        content: str = "",
        phase: str = "draft",
        template_type: str = "custom",
        deadline: Optional[datetime] = None,
        milestones: Optional[List[Dict[str, Any]]] = None,
        tags: Optional[List[str]] = None,
    ) -> dict:
        """Create a new goal document for MongoDB."""
        return {
            "user_id": ObjectId(user_id),
            "title": title,
            "content": content,
            "phase": phase,
            "template_type": template_type,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "metadata": {
                "deadline": deadline,
                "milestones": milestones or [],
                "tags": tags or [],
            }
        }

    @staticmethod
    def serialize_goal(goal_doc: dict) -> Optional[dict]:
        """Serialize goal document for API response."""
        if not goal_doc:
            return None

        return {
            "id": str(goal_doc["_id"]),
            "user_id": str(goal_doc["user_id"]),
            "title": goal_doc["title"],
            "content": goal_doc.get("content", ""),
            "phase": goal_doc["phase"],
            "template_type": goal_doc.get("template_type", "custom"),
            "created_at": goal_doc["created_at"].isoformat() if isinstance(goal_doc["created_at"], datetime) else goal_doc["created_at"],
            "updated_at": goal_doc["updated_at"].isoformat() if isinstance(goal_doc["updated_at"], datetime) else goal_doc["updated_at"],
            "metadata": {
                "deadline": (
                    goal_doc.get("metadata", {}).get("deadline").isoformat()
                    if isinstance(goal_doc.get("metadata", {}).get("deadline"), datetime)
                    else goal_doc.get("metadata", {}).get("deadline")
                ),
                "milestones": goal_doc.get("metadata", {}).get("milestones", []),
                "tags": goal_doc.get("metadata", {}).get("tags", []),
                "content_format": goal_doc.get("metadata", {}).get("content_format"),
            }
        }

    @staticmethod
    def serialize_goals(goals: List[dict]) -> List[dict]:
        """Serialize multiple goal documents for API response."""
        return [GoalModel.serialize_goal(goal) for goal in goals if goal]


class GoalTemplateModel:
    """
    Goal template model for predefined goal structures.
    """

    # Predefined templates
    TEMPLATES = {
        "smart": {
            "name": "SMART Goal",
            "description": "Specific, Measurable, Achievable, Relevant, Time-bound goal framework",
            "template_content": """# SMART Goal Template

## Specific
What exactly do you want to accomplish? Be as detailed as possible.


## Measurable
How will you measure your progress? What metrics will you use?


## Achievable
Is this goal realistic? What resources and capabilities do you have?


## Relevant
Why is this goal important to you? How does it align with your values?


## Time-bound
What is your deadline? Set specific milestones along the way.

""",
            "fields": [
                {"name": "specific", "label": "Specific", "type": "textarea", "required": True},
                {"name": "measurable", "label": "Measurable", "type": "textarea", "required": True},
                {"name": "achievable", "label": "Achievable", "type": "textarea", "required": True},
                {"name": "relevant", "label": "Relevant", "type": "textarea", "required": True},
                {"name": "time_bound", "label": "Time-bound", "type": "textarea", "required": True},
            ],
            "is_active": True,
        },
        "okr": {
            "name": "OKR (Objectives and Key Results)",
            "description": "Goal-setting framework focusing on objectives and measurable key results",
            "template_content": """# OKR Template

## Objective
What is your inspiring, qualitative goal?


## Key Result 1
What measurable outcome will indicate progress? (Target: )


## Key Result 2
What measurable outcome will indicate progress? (Target: )


## Key Result 3
What measurable outcome will indicate progress? (Target: )


## Initiatives
What actions will you take to achieve these key results?

""",
            "fields": [
                {"name": "objective", "label": "Objective", "type": "textarea", "required": True},
                {"name": "key_result_1", "label": "Key Result 1", "type": "text", "required": True},
                {"name": "key_result_2", "label": "Key Result 2", "type": "text", "required": False},
                {"name": "key_result_3", "label": "Key Result 3", "type": "text", "required": False},
                {"name": "initiatives", "label": "Initiatives", "type": "textarea", "required": False},
            ],
            "is_active": True,
        },
        "custom": {
            "name": "Custom Goal",
            "description": "Free-form goal template for any type of goal",
            "template_content": """# My Goal

## What I Want to Achieve


## Why This Matters


## My Action Plan


## Timeline and Milestones


## Potential Obstacles and Solutions

""",
            "fields": [
                {"name": "goal", "label": "What I Want to Achieve", "type": "textarea", "required": True},
                {"name": "why", "label": "Why This Matters", "type": "textarea", "required": False},
                {"name": "action_plan", "label": "Action Plan", "type": "textarea", "required": False},
                {"name": "timeline", "label": "Timeline", "type": "textarea", "required": False},
                {"name": "obstacles", "label": "Obstacles and Solutions", "type": "textarea", "required": False},
            ],
            "is_active": True,
        },
    }

    @staticmethod
    def get_template(template_type: str) -> Optional[dict]:
        """Get a template by type."""
        template = GoalTemplateModel.TEMPLATES.get(template_type)
        if template:
            return {
                "type": template_type,
                **template
            }
        return None

    @staticmethod
    def get_all_templates() -> List[dict]:
        """Get all available templates."""
        return [
            {"type": template_type, **template}
            for template_type, template in GoalTemplateModel.TEMPLATES.items()
            if template.get("is_active", True)
        ]

    @staticmethod
    def create_goal_from_template(
        user_id: str,
        template_type: str,
        title: str,
        field_values: Optional[Dict[str, str]] = None,
        deadline: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[dict]:
        """Create a goal document pre-filled with template content."""
        template = GoalTemplateModel.TEMPLATES.get(template_type)
        if not template:
            return None

        # Start with template content
        content = template["template_content"]

        # If field values provided, substitute them into content
        if field_values:
            for field in template["fields"]:
                field_name = field["name"]
                if field_name in field_values and field_values[field_name]:
                    # Simple substitution - replace empty sections with values
                    placeholder = f"## {field['label']}\n\n"
                    replacement = f"## {field['label']}\n{field_values[field_name]}\n"
                    content = content.replace(placeholder, replacement)

        return GoalModel.create_goal_document(
            user_id=user_id,
            title=title,
            content=content,
            phase="draft",
            template_type=template_type,
            deadline=deadline,
            tags=tags,
        )
