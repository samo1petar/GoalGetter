"""
Celery application configuration for GoalGetter.
Handles background task processing and scheduled jobs.
"""
from celery import Celery
from celery.schedules import crontab
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create Celery application
celery_app = Celery(
    "goalgetter",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.celery_tasks"],
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    accept_content=["json"],
    result_serializer=settings.CELERY_RESULT_SERIALIZER,

    # Timezone
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=settings.CELERY_ENABLE_UTC,

    # Task settings
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,

    # Result settings
    result_expires=3600,  # Results expire after 1 hour

    # Error handling
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Update meeting statuses every 5 minutes
    "update-meeting-statuses": {
        "task": "app.tasks.celery_tasks.update_meeting_statuses_task",
        "schedule": 300.0,  # Every 5 minutes
        "options": {"queue": "default"},
    },
    # Send meeting reminders every hour
    "send-meeting-reminders": {
        "task": "app.tasks.celery_tasks.send_meeting_reminders_task",
        "schedule": 3600.0,  # Every hour
        "options": {"queue": "default"},
    },
    # Cleanup old messages daily at 3 AM UTC
    "cleanup-old-messages": {
        "task": "app.tasks.celery_tasks.cleanup_old_messages_task",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "default"},
    },
}

# Optional: Configure different queues
celery_app.conf.task_queues = {
    "default": {
        "exchange": "default",
        "routing_key": "default",
    },
    "email": {
        "exchange": "email",
        "routing_key": "email",
    },
    "high_priority": {
        "exchange": "high_priority",
        "routing_key": "high_priority",
    },
}

# Default queue
celery_app.conf.task_default_queue = "default"

logger.info("Celery app configured successfully")
