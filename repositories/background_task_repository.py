"""
Repository for BackgroundTask model operations.
Handles CRUD operations and status queries for background tasks.
"""

from typing import Optional, List
from datetime import datetime
from sqlmodel import Session, select
from models.background_task import BackgroundTask
from repositories.base_repository import BaseRepository


class BackgroundTaskRepository(BaseRepository[BackgroundTask]):
    """Repository for managing background tasks."""

    def __init__(self, db_session: Session):
        super().__init__(db_session, BackgroundTask)

    def create_task(
        self,
        task_type: str,
        related_entity_type: str,
        related_entity_id: str,
    ) -> BackgroundTask:
        """
        Create a new background task with INITIATED status.

        Args:
            task_type: Type of task (e.g., "session_summarization")
            related_entity_type: Type of related entity (e.g., "interview_session")
            related_entity_id: ID of the related entity

        Returns:
            Created BackgroundTask record
        """
        task = BackgroundTask(
            task_type=task_type,
            status="INITIATED",
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
        )
        return self.create(task)

    def get_by_id(self, task_id: str) -> Optional[BackgroundTask]:
        """Get a task by its ID."""
        statement = select(BackgroundTask).where(BackgroundTask.id == task_id)
        return self.db.exec(statement).first()

    def update_status(
        self,
        task_id: str,
        status: str,
        result: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[BackgroundTask]:
        """
        Update task status and optionally result or error message.

        Args:
            task_id: Task ID
            status: New status (PENDING, SUCCESS, FAILED)
            result: JSON result if applicable
            error_message: Error message if task failed

        Returns:
            Updated BackgroundTask record or None if not found
        """
        task = self.get_by_id(task_id)
        if not task:
            return None

        task.status = status

        if status == "PENDING" and task.started_at is None:
            task.started_at = datetime.utcnow()

        if status in ["SUCCESS", "FAILED"]:
            task.completed_at = datetime.utcnow()

        if result:
            task.result = result

        if error_message:
            task.error_message = error_message

        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        return task

    def get_by_entity(
        self,
        related_entity_type: str,
        related_entity_id: str,
    ) -> List[BackgroundTask]:
        """
        Get all tasks related to a specific entity.

        Args:
            related_entity_type: Type of entity
            related_entity_id: ID of entity

        Returns:
            List of BackgroundTask records
        """
        statement = select(BackgroundTask).where(
            (BackgroundTask.related_entity_type == related_entity_type)
            & (BackgroundTask.related_entity_id == related_entity_id)
        ).order_by(BackgroundTask.created_at.desc())
        return self.db.exec(statement).all()

    def get_pending_tasks(self) -> List[BackgroundTask]:
        """Get all pending or initiated tasks."""
        statement = select(BackgroundTask).where(
            BackgroundTask.status.in_(["INITIATED", "PENDING"])
        ).order_by(BackgroundTask.created_at)
        return self.db.exec(statement).all()

    def get_failed_tasks(self) -> List[BackgroundTask]:
        """Get all failed tasks."""
        statement = select(BackgroundTask).where(
            BackgroundTask.status == "FAILED"
        ).order_by(BackgroundTask.created_at.desc())
        return self.db.exec(statement).all()
