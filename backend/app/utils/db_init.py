"""
Database initialization utilities.
Used for seeding initial data and verifying database setup.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

from app.core.database import Database
from app.core.config import settings

logger = logging.getLogger(__name__)


async def init_database():
    """Initialize database with required collections and data."""
    try:
        await Database.connect_db()
        db = Database.get_db()

        logger.info("Starting database initialization...")

        # Create collections if they don't exist
        collections = await db.list_collection_names()

        required_collections = ["users", "goals", "meetings", "chat_messages", "goal_templates"]

        for collection_name in required_collections:
            if collection_name not in collections:
                await db.create_collection(collection_name)
                logger.info(f"Created collection: {collection_name}")
            else:
                logger.info(f"Collection already exists: {collection_name}")

        # Seed goal templates
        await seed_goal_templates(db)

        logger.info("Database initialization completed successfully")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    finally:
        await Database.close_db()


async def seed_goal_templates(db: AsyncIOMotorDatabase):
    """Seed initial goal templates."""
    templates = [
        {
            "name": "SMART",
            "description": "SMART Goal Framework - Specific, Measurable, Achievable, Relevant, Time-bound",
            "template_content": """# SMART Goal

## Specific
[What exactly do you want to achieve?]

## Measurable
[How will you measure success? What metrics will you track?]

## Achievable
[Is this realistic given your resources, time, and capabilities?]

## Relevant
[Why does this matter to you? How does it align with your values and long-term objectives?]

## Time-bound
[When will you achieve this goal? What's your deadline?]

## Action Steps
1. [First action step]
2. [Second action step]
3. [Third action step]
""",
            "fields": [
                {"name": "specific", "label": "Specific", "type": "textarea"},
                {"name": "measurable", "label": "Measurable", "type": "textarea"},
                {"name": "achievable", "label": "Achievable", "type": "textarea"},
                {"name": "relevant", "label": "Relevant", "type": "textarea"},
                {"name": "time_bound", "label": "Time-bound", "type": "text"},
            ],
            "is_active": True,
        },
        {
            "name": "OKR",
            "description": "Objectives and Key Results Framework",
            "template_content": """# OKR - Objectives and Key Results

## Objective
[What do you want to accomplish? This should be ambitious and inspirational.]

## Key Results
### Key Result 1
[Measurable outcome that indicates progress toward the objective]

### Key Result 2
[Measurable outcome that indicates progress toward the objective]

### Key Result 3
[Measurable outcome that indicates progress toward the objective]

## Timeline
[Quarter/Month/Year]

## Initiatives
- [Initiative 1: Specific actions to achieve key results]
- [Initiative 2: Specific actions to achieve key results]
- [Initiative 3: Specific actions to achieve key results]
""",
            "fields": [
                {"name": "objective", "label": "Objective", "type": "textarea"},
                {"name": "key_result_1", "label": "Key Result 1", "type": "textarea"},
                {"name": "key_result_2", "label": "Key Result 2", "type": "textarea"},
                {"name": "key_result_3", "label": "Key Result 3", "type": "textarea"},
                {"name": "timeline", "label": "Timeline", "type": "text"},
            ],
            "is_active": True,
        },
        {
            "name": "Custom",
            "description": "Start from scratch with a blank canvas",
            "template_content": """# My Goal

## Goal Description
[Describe your goal here]

## Why This Matters
[Why is this goal important to you?]

## Success Criteria
[How will you know when you've achieved this goal?]

## Action Plan
- [Action 1]
- [Action 2]
- [Action 3]

## Timeline
[When will you complete this?]

## Potential Obstacles
[What might get in your way?]

## Support & Resources
[Who or what can help you achieve this?]
""",
            "fields": [],
            "is_active": True,
        },
    ]

    # Check if templates already exist
    existing_count = await db.goal_templates.count_documents({})

    if existing_count == 0:
        await db.goal_templates.insert_many(templates)
        logger.info(f"Seeded {len(templates)} goal templates")
    else:
        logger.info(f"Goal templates already exist ({existing_count} templates)")


async def clear_database():
    """Clear all collections (use with caution!)."""
    try:
        await Database.connect_db()
        db = Database.get_db()

        logger.warning("Clearing all database collections...")

        collections = await db.list_collection_names()

        for collection_name in collections:
            if collection_name != "system.indexes":
                await db[collection_name].drop()
                logger.info(f"Dropped collection: {collection_name}")

        logger.warning("Database cleared successfully")

    except Exception as e:
        logger.error(f"Database clear failed: {e}")
        raise
    finally:
        await Database.close_db()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        print("WARNING: This will delete all data!")
        response = input("Are you sure? (yes/no): ")
        if response.lower() == "yes":
            asyncio.run(clear_database())
        else:
            print("Aborted")
    else:
        asyncio.run(init_database())
