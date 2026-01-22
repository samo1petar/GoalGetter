"""
Goal Tool Handler for AI Coach.
Executes goal manipulation tools called by Claude.

Content Format Handling:
- AI Coach writes goal content as Markdown for rich formatting
- Frontend GoalEditor converts Markdown to BlockNote blocks for display
- Content can be stored as Markdown (from AI) or BlockNote JSON (from user edits)
- The 'content_format' metadata field indicates the format ('markdown' or 'blocknote_json')
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.goal import GoalModel

logger = logging.getLogger(__name__)

# Content format constants
CONTENT_FORMAT_MARKDOWN = "markdown"
CONTENT_FORMAT_BLOCKNOTE = "blocknote_json"


class GoalToolHandler:
    """
    Handles execution of goal-related tools called by the AI Coach.
    """

    def __init__(self, db: AsyncIOMotorDatabase, user_id: str):
        """
        Initialize the tool handler.

        Args:
            db: MongoDB database instance
            user_id: The user's ID
        """
        self.db = db
        self.user_id = user_id

    async def execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        active_goal_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a goal tool and return the result.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool
            active_goal_id: ID of the currently active goal in editor (for 'current' reference)

        Returns:
            Dict with success status, goal_id, goal data, or error
        """
        try:
            if tool_name == "create_goal":
                return await self._create_goal(tool_input)
            elif tool_name == "update_goal":
                return await self._update_goal(tool_input, active_goal_id)
            elif tool_name == "set_goal_phase":
                return await self._set_goal_phase(tool_input, active_goal_id)
            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}",
                }
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def _create_goal(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new goal from tool input.

        Content Format:
        - AI Coach provides content as Markdown for rich formatting
        - Frontend GoalEditor automatically converts Markdown to BlockNote blocks
        - The content_format field in metadata indicates the format
        """
        title = tool_input.get("title", "Untitled Goal")
        content = tool_input.get("content", "")
        template_type = tool_input.get("template_type", "custom")
        deadline = tool_input.get("deadline")
        milestones = tool_input.get("milestones", [])
        tags = tool_input.get("tags", [])
        # Content format hint from tool input, defaults to markdown for AI-created content
        content_format = tool_input.get("content_format", CONTENT_FORMAT_MARKDOWN)

        # Format milestones
        formatted_milestones = []
        for m in milestones:
            milestone = {
                "title": m.get("title", ""),
                "description": m.get("description", ""),
                "target_date": m.get("target_date"),
                "completed": False,
                "completed_at": None,
            }
            formatted_milestones.append(milestone)

        # Create goal document
        goal_doc = GoalModel.create_goal_document(
            user_id=self.user_id,
            title=title,
            content=content,
            phase="draft",  # AI-created goals start as drafts
            template_type=template_type,
        )

        # Add metadata including content format
        goal_doc["metadata"]["deadline"] = deadline
        goal_doc["metadata"]["milestones"] = formatted_milestones
        goal_doc["metadata"]["tags"] = tags
        goal_doc["metadata"]["content_format"] = content_format

        # Insert into database
        result = await self.db.goals.insert_one(goal_doc)
        goal_doc["_id"] = result.inserted_id

        # Serialize for response
        serialized_goal = GoalModel.serialize_goal(goal_doc)

        logger.info(f"AI Coach created goal: {serialized_goal['id']} for user {self.user_id}")

        return {
            "success": True,
            "goal_id": serialized_goal["id"],
            "goal": serialized_goal,
        }

    async def _create_goal_minimal(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Create a minimal goal with just title - returns goal_id for focus."""
        try:
            title = tool_input.get("title", "New Goal")
            template_type = tool_input.get("template_type", "custom")

            # Create minimal goal document - content_format will be set
            # when _update_goal populates the content
            goal_doc = GoalModel.create_goal_document(
                user_id=self.user_id,
                title=title,
                content="",  # Empty content - will be populated by _update_goal
                template_type=template_type,
            )

            result = await self.db.goals.insert_one(goal_doc)
            goal_id = str(result.inserted_id)

            return {"success": True, "goal_id": goal_id}
        except Exception as e:
            logger.error(f"Error creating minimal goal: {e}")
            return {"success": False, "error": str(e)}

    async def _update_goal(
        self,
        tool_input: Dict[str, Any],
        active_goal_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing goal."""
        goal_id = tool_input.get("goal_id", "")

        # Handle 'current' reference
        if goal_id == "current":
            if not active_goal_id:
                return {
                    "success": False,
                    "error": "No active goal in editor to update",
                }
            goal_id = active_goal_id

        # Validate goal_id format
        if not ObjectId.is_valid(goal_id):
            return {
                "success": False,
                "error": f"Invalid goal ID: {goal_id}",
            }

        # Find the goal
        goal = await self.db.goals.find_one({
            "_id": ObjectId(goal_id),
            "user_id": ObjectId(self.user_id),
        })

        if not goal:
            return {
                "success": False,
                "error": f"Goal not found: {goal_id}",
            }

        # Build update dict
        update_fields = {"updated_at": datetime.utcnow()}

        # Only update fields that are not None (strict mode sends all fields)
        if tool_input.get("title") is not None:
            update_fields["title"] = tool_input["title"]

        if tool_input.get("content") is not None:
            update_fields["content"] = tool_input["content"]
            # When AI updates content, mark it as Markdown format
            content_format = tool_input.get("content_format", CONTENT_FORMAT_MARKDOWN)
            update_fields["metadata.content_format"] = content_format

        if tool_input.get("deadline") is not None:
            update_fields["metadata.deadline"] = tool_input["deadline"]

        if tool_input.get("tags") is not None:
            update_fields["metadata.tags"] = tool_input["tags"]

        # Handle milestones
        if tool_input.get("milestones") is not None:
            # Replace all milestones
            formatted_milestones = []
            for m in tool_input["milestones"]:
                milestone = {
                    "title": m.get("title", ""),
                    "description": m.get("description", ""),
                    "target_date": m.get("target_date"),
                    "completed": m.get("completed", False),
                    "completed_at": None,
                }
                formatted_milestones.append(milestone)
            update_fields["metadata.milestones"] = formatted_milestones

        elif tool_input.get("add_milestone") is not None:
            # Add a single milestone
            new_milestone = {
                "title": tool_input["add_milestone"].get("title", ""),
                "description": tool_input["add_milestone"].get("description", ""),
                "target_date": tool_input["add_milestone"].get("target_date"),
                "completed": False,
                "completed_at": None,
            }
            await self.db.goals.update_one(
                {"_id": ObjectId(goal_id)},
                {"$push": {"metadata.milestones": new_milestone}}
            )

        # Apply updates
        if update_fields:
            await self.db.goals.update_one(
                {"_id": ObjectId(goal_id)},
                {"$set": update_fields}
            )

        # Fetch updated goal
        updated_goal = await self.db.goals.find_one({"_id": ObjectId(goal_id)})
        serialized_goal = GoalModel.serialize_goal(updated_goal)

        logger.info(f"AI Coach updated goal: {goal_id} for user {self.user_id}")

        return {
            "success": True,
            "goal_id": goal_id,
            "goal": serialized_goal,
        }

    async def _set_goal_phase(
        self,
        tool_input: Dict[str, Any],
        active_goal_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Change a goal's phase."""
        goal_id = tool_input.get("goal_id", "")
        new_phase = tool_input.get("phase", "")

        # Validate phase
        valid_phases = ["draft", "active", "completed", "archived"]
        if new_phase not in valid_phases:
            return {
                "success": False,
                "error": f"Invalid phase: {new_phase}. Must be one of: {valid_phases}",
            }

        # Handle 'current' reference
        if goal_id == "current":
            if not active_goal_id:
                return {
                    "success": False,
                    "error": "No active goal in editor to update",
                }
            goal_id = active_goal_id

        # Validate goal_id format
        if not ObjectId.is_valid(goal_id):
            return {
                "success": False,
                "error": f"Invalid goal ID: {goal_id}",
            }

        # Find the goal
        goal = await self.db.goals.find_one({
            "_id": ObjectId(goal_id),
            "user_id": ObjectId(self.user_id),
        })

        if not goal:
            return {
                "success": False,
                "error": f"Goal not found: {goal_id}",
            }

        # Update phase
        update_fields = {
            "phase": new_phase,
            "updated_at": datetime.utcnow(),
        }

        await self.db.goals.update_one(
            {"_id": ObjectId(goal_id)},
            {"$set": update_fields}
        )

        # Fetch updated goal
        updated_goal = await self.db.goals.find_one({"_id": ObjectId(goal_id)})
        serialized_goal = GoalModel.serialize_goal(updated_goal)

        logger.info(f"AI Coach changed goal {goal_id} phase to {new_phase} for user {self.user_id}")

        return {
            "success": True,
            "goal_id": goal_id,
            "goal": serialized_goal,
        }
