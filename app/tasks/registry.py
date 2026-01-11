"""
Background task registry for document builds.

Simple in-memory registry for tracking async tasks.
Tasks survive page navigation but not server restart.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class TaskInfo:
    """Information about a running or completed task."""
    task_id: UUID
    status: TaskStatus
    progress: int = 0  # 0-100
    message: str = ""
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Task metadata
    project_id: Optional[UUID] = None
    doc_type_id: Optional[str] = None


# Global registry (single process)
_tasks: dict[UUID, TaskInfo] = {}


def get_task(task_id: UUID) -> Optional[TaskInfo]:
    """Get task info by ID."""
    return _tasks.get(task_id)


def set_task(info: TaskInfo) -> None:
    """Create or update a task."""
    info.updated_at = datetime.now(timezone.utc)
    _tasks[info.task_id] = info
    logger.debug(f"Task {info.task_id}: {info.status.value} - {info.message} ({info.progress}%)")


def update_task(
    task_id: UUID,
    status: Optional[TaskStatus] = None,
    progress: Optional[int] = None,
    message: Optional[str] = None,
    result: Any = None,
    error: Optional[str] = None
) -> Optional[TaskInfo]:
    """Update specific fields of an existing task."""
    task = _tasks.get(task_id)
    if not task:
        return None
    
    if status is not None:
        task.status = status
    if progress is not None:
        task.progress = progress
    if message is not None:
        task.message = message
    if result is not None:
        task.result = result
    if error is not None:
        task.error = error
    
    task.updated_at = datetime.now(timezone.utc)
    logger.debug(f"Task {task_id}: {task.status.value} - {task.message} ({task.progress}%)")
    return task


def find_task(project_id: UUID, doc_type_id: str) -> Optional[TaskInfo]:
    """Find an active task for a project/doc_type combination."""
    for task in _tasks.values():
        if (task.project_id == project_id and 
            task.doc_type_id == doc_type_id and
            task.status in (TaskStatus.PENDING, TaskStatus.RUNNING)):
            return task
    return None


def cleanup_old_tasks(max_age_hours: int = 1) -> int:
    """Remove completed/failed tasks older than max_age_hours."""
    cutoff = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
    to_remove = [
        tid for tid, task in _tasks.items()
        if task.status in (TaskStatus.COMPLETE, TaskStatus.FAILED)
        and task.updated_at.timestamp() < cutoff
    ]
    for tid in to_remove:
        del _tasks[tid]
    return len(to_remove)
