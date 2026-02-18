"""Celery configuration and initialization."""
import sys
import os

# Add root project to Python path for module discovery
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from celery import Celery
from config.settings import settings
import platform

# Initialize Celery app
celery_app = Celery("fabric")

# Configure Celery with Redis
celery_config = {
    "broker_url": settings.CELERY_BROKER_URL,
    "result_backend": settings.CELERY_RESULT_BACKEND,
    "task_serializer": "json",
    "accept_content": ["json"],
    "result_serializer": "json",
    "timezone": "UTC",
    "enable_utc": True,
    "task_track_started": True,
    "task_time_limit": 30 * 60,  # 30 minutes hard limit
    "task_soft_time_limit": 25 * 60,  # 25 minutes soft limit
    "result_expires": 60 * 60 * 24, # 24 hours to expire task results
}

# Use threads pool on Windows (prefork doesn't work on Windows)
if platform.system() == "Windows":
    celery_config["worker_pool"] = "threads"
    celery_config["worker_concurrency"] = 4

celery_app.conf.update(celery_config)

# Auto-discover tasks from registered apps
celery_app.autodiscover_tasks(["agents.summarization"])

