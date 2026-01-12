"""
Goal service handling goal CRUD operations and business logic.
"""
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
import math

from app.models.goal import GoalModel, GoalTemplateModel
from app.schemas.goal import (
    GoalCreate,
    GoalUpdate,
    GoalFromTemplateCreate,
    MilestoneSchema,
)


class GoalService:
    """Service for goal operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def create_goal(
        self,
        user_id: str,
        goal_data: GoalCreate,
    ) -> Dict[str, Any]:
        """
        Create a new goal for a user.
        """
        # Build milestones list if provided
        milestones = None
        if goal_data.milestones:
            milestones = [
                {
                    "title": m.title,
                    "description": m.description,
                    "target_date": m.target_date,
                    "completed": m.completed,
                    "completed_at": m.completed_at,
                }
                for m in goal_data.milestones
            ]

        # Create goal document
        goal_doc = GoalModel.create_goal_document(
            user_id=user_id,
            title=goal_data.title,
            content=goal_data.content,
            phase=goal_data.phase,
            template_type=goal_data.template_type,
            deadline=goal_data.deadline,
            milestones=milestones,
            tags=goal_data.tags,
        )

        # Insert into database
        result = await self.db.goals.insert_one(goal_doc)
        goal_doc["_id"] = result.inserted_id

        # Serialize and return
        return GoalModel.serialize_goal(goal_doc)

    async def get_goal_by_id(
        self,
        goal_id: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a goal by ID. Ensures user owns the goal.
        """
        try:
            goal = await self.db.goals.find_one({
                "_id": ObjectId(goal_id),
                "user_id": ObjectId(user_id),
            })
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid goal ID format"
            )

        if not goal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Goal not found"
            )

        return GoalModel.serialize_goal(goal)

    async def get_user_goals(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        phase: Optional[str] = None,
        template_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get paginated list of goals for a user with optional filters.
        """
        # Build query filter
        query: Dict[str, Any] = {"user_id": ObjectId(user_id)}

        if phase:
            query["phase"] = phase

        if template_type:
            query["template_type"] = template_type

        if tags:
            query["metadata.tags"] = {"$all": tags}

        if search:
            # Search in title and content
            query["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"content": {"$regex": search, "$options": "i"}},
            ]

        # Calculate skip value
        skip = (page - 1) * page_size

        # Determine sort direction
        sort_direction = -1 if sort_order == "desc" else 1

        # Get total count
        total = await self.db.goals.count_documents(query)

        # Get goals with pagination and sorting
        cursor = self.db.goals.find(query).sort(sort_by, sort_direction).skip(skip).limit(page_size)
        goals = await cursor.to_list(length=page_size)

        return GoalModel.serialize_goals(goals), total

    async def update_goal(
        self,
        goal_id: str,
        user_id: str,
        goal_data: GoalUpdate,
    ) -> Dict[str, Any]:
        """
        Update an existing goal.
        """
        # Build update document
        update_doc = {"updated_at": datetime.utcnow()}

        if goal_data.title is not None:
            update_doc["title"] = goal_data.title

        if goal_data.content is not None:
            update_doc["content"] = goal_data.content

        if goal_data.phase is not None:
            update_doc["phase"] = goal_data.phase

        if goal_data.deadline is not None:
            update_doc["metadata.deadline"] = goal_data.deadline

        if goal_data.milestones is not None:
            update_doc["metadata.milestones"] = [
                {
                    "title": m.title,
                    "description": m.description,
                    "target_date": m.target_date,
                    "completed": m.completed,
                    "completed_at": m.completed_at,
                }
                for m in goal_data.milestones
            ]

        if goal_data.tags is not None:
            update_doc["metadata.tags"] = goal_data.tags

        try:
            result = await self.db.goals.find_one_and_update(
                {
                    "_id": ObjectId(goal_id),
                    "user_id": ObjectId(user_id),
                },
                {"$set": update_doc},
                return_document=True,
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid goal ID format"
            )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Goal not found"
            )

        return GoalModel.serialize_goal(result)

    async def update_goal_phase(
        self,
        goal_id: str,
        user_id: str,
        phase: str,
    ) -> Dict[str, Any]:
        """
        Update goal phase.
        """
        try:
            result = await self.db.goals.find_one_and_update(
                {
                    "_id": ObjectId(goal_id),
                    "user_id": ObjectId(user_id),
                },
                {
                    "$set": {
                        "phase": phase,
                        "updated_at": datetime.utcnow(),
                    }
                },
                return_document=True,
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid goal ID format"
            )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Goal not found"
            )

        return GoalModel.serialize_goal(result)

    async def delete_goal(
        self,
        goal_id: str,
        user_id: str,
    ) -> bool:
        """
        Delete a goal.
        """
        try:
            result = await self.db.goals.delete_one({
                "_id": ObjectId(goal_id),
                "user_id": ObjectId(user_id),
            })
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid goal ID format"
            )

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Goal not found"
            )

        return True

    async def create_goal_from_template(
        self,
        user_id: str,
        template_data: GoalFromTemplateCreate,
    ) -> Dict[str, Any]:
        """
        Create a new goal from a template.
        """
        # Get template
        template = GoalTemplateModel.get_template(template_data.template_type)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid template type: {template_data.template_type}"
            )

        # Create goal document from template
        goal_doc = GoalTemplateModel.create_goal_from_template(
            user_id=user_id,
            template_type=template_data.template_type,
            title=template_data.title,
            field_values=template_data.field_values,
            deadline=template_data.deadline,
            tags=template_data.tags,
        )

        if not goal_doc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create goal from template"
            )

        # Insert into database
        result = await self.db.goals.insert_one(goal_doc)
        goal_doc["_id"] = result.inserted_id

        return GoalModel.serialize_goal(goal_doc)

    async def get_goal_statistics(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Get goal statistics for a user.
        """
        pipeline = [
            {"$match": {"user_id": ObjectId(user_id)}},
            {
                "$group": {
                    "_id": "$phase",
                    "count": {"$sum": 1},
                }
            }
        ]

        cursor = self.db.goals.aggregate(pipeline)
        results = await cursor.to_list(length=10)

        # Build statistics
        stats = {
            "total": 0,
            "by_phase": {
                "draft": 0,
                "active": 0,
                "completed": 0,
                "archived": 0,
            }
        }

        for result in results:
            phase = result["_id"]
            count = result["count"]
            stats["total"] += count
            if phase in stats["by_phase"]:
                stats["by_phase"][phase] = count

        return stats
