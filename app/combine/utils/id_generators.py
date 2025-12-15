"""
ID Generators for The Combine

Generates unique IDs for projects, epics, stories, and other artifacts
following RSP-1 path conventions.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.combine.models import Artifact


async def generate_epic_id(project_id: str, db: AsyncSession) -> str:
    """
    Generate next epic ID for a project.
    
    Format: E001, E002, E003, etc.
    
    Args:
        project_id: Project identifier (e.g., "AUTH", "PROJ")
        db: Database session
        
    Returns:
        Next epic ID (e.g., "E001")
        
    Example:
        epic_id = await generate_epic_id("AUTH", db)
        # Returns: "E001" (or next available)
    """
    # Query for highest epic number in this project
    query = (
        select(Artifact.artifact_path)
        .where(Artifact.artifact_path.like(f"{project_id}/E%"))
        .where(Artifact.artifact_type == "epic")
    )
    
    result = await db.execute(query)
    epic_paths = result.scalars().all()
    
    if not epic_paths:
        return "E001"
    
    # Extract epic numbers and find max
    epic_numbers = []
    for path in epic_paths:
        parts = path.split("/")
        if len(parts) >= 2 and parts[1].startswith("E"):
            try:
                num = int(parts[1][1:])  # Remove 'E' and parse number
                epic_numbers.append(num)
            except ValueError:
                continue
    
    if not epic_numbers:
        return "E001"
    
    next_num = max(epic_numbers) + 1
    return f"E{next_num:03d}"


async def generate_story_id(project_id: str, epic_id: str, db: AsyncSession) -> str:
    """
    Generate next story ID for an epic.
    
    Format: S001, S002, S003, etc.
    
    Args:
        project_id: Project identifier (e.g., "AUTH")
        epic_id: Epic identifier (e.g., "E001")
        db: Database session
        
    Returns:
        Next story ID (e.g., "S001")
        
    Example:
        story_id = await generate_story_id("AUTH", "E001", db)
        # Returns: "S001" (or next available)
    """
    # Query for highest story number in this epic
    query = (
        select(Artifact.artifact_path)
        .where(Artifact.artifact_path.like(f"{project_id}/{epic_id}/S%"))
        .where(Artifact.artifact_type == "story")
    )
    
    result = await db.execute(query)
    story_paths = result.scalars().all()
    
    if not story_paths:
        return "S001"
    
    # Extract story numbers and find max
    story_numbers = []
    for path in story_paths:
        parts = path.split("/")
        if len(parts) >= 3 and parts[2].startswith("S"):
            try:
                num = int(parts[2][1:])  # Remove 'S' and parse number
                story_numbers.append(num)
            except ValueError:
                continue
    
    if not story_numbers:
        return "S001"
    
    next_num = max(story_numbers) + 1
    return f"S{next_num:03d}"


async def generate_task_id(project_id: str, epic_id: str, story_id: str, db: AsyncSession) -> str:
    """
    Generate next task ID for a story.
    
    Format: T001, T002, T003, etc.
    
    Args:
        project_id: Project identifier (e.g., "AUTH")
        epic_id: Epic identifier (e.g., "E001")
        story_id: Story identifier (e.g., "S001")
        db: Database session
        
    Returns:
        Next task ID (e.g., "T001")
        
    Example:
        task_id = await generate_task_id("AUTH", "E001", "S001", db)
        # Returns: "T001" (or next available)
    """
    # Query for highest task number in this story
    query = (
        select(Artifact.artifact_path)
        .where(Artifact.artifact_path.like(f"{project_id}/{epic_id}/{story_id}/T%"))
        .where(Artifact.artifact_type == "task")
    )
    
    result = await db.execute(query)
    task_paths = result.scalars().all()
    
    if not task_paths:
        return "T001"
    
    # Extract task numbers and find max
    task_numbers = []
    for path in task_paths:
        parts = path.split("/")
        if len(parts) >= 4 and parts[3].startswith("T"):
            try:
                num = int(parts[3][1:])  # Remove 'T' and parse number
                task_numbers.append(num)
            except ValueError:
                continue
    
    if not task_numbers:
        return "T001"
    
    next_num = max(task_numbers) + 1
    return f"T{next_num:03d}"


def parse_artifact_path(artifact_path: str) -> dict:
    """
    Parse an RSP-1 artifact path into components.
    
    Args:
        artifact_path: Path like "PROJ/E001/S002/T003"
        
    Returns:
        Dictionary with parsed components:
        {
            "project_id": "PROJ",
            "epic_id": "E001",      # if present
            "story_id": "S002",     # if present
            "task_id": "T003",      # if present
            "level": "task"         # project, epic, story, or task
        }
        
    Example:
        parts = parse_artifact_path("AUTH/E001/S002")
        # Returns: {
        #   "project_id": "AUTH",
        #   "epic_id": "E001",
        #   "story_id": "S002",
        #   "level": "story"
        # }
    """
    parts = artifact_path.split("/")
    
    result = {}
    
    # Always has project
    if len(parts) >= 1:
        result["project_id"] = parts[0]
        result["level"] = "project"
    
    # May have epic
    if len(parts) >= 2:
        result["epic_id"] = parts[1]
        result["level"] = "epic"
    
    # May have story
    if len(parts) >= 3:
        result["story_id"] = parts[2]
        result["level"] = "story"
    
    # May have task
    if len(parts) >= 4:
        result["task_id"] = parts[3]
        result["level"] = "task"
    
    return result


def build_artifact_path(project_id: str, epic_id: str = None, story_id: str = None, task_id: str = None) -> str:
    """
    Build an RSP-1 artifact path from components.
    
    Args:
        project_id: Project identifier (required)
        epic_id: Epic identifier (optional)
        story_id: Story identifier (optional)
        task_id: Task identifier (optional)
        
    Returns:
        Complete artifact path
        
    Example:
        path = build_artifact_path("AUTH", "E001", "S002")
        # Returns: "AUTH/E001/S002"
    """
    path_parts = [project_id]
    
    if epic_id:
        path_parts.append(epic_id)
    
    if story_id:
        path_parts.append(story_id)
    
    if task_id:
        path_parts.append(task_id)
    
    return "/".join(path_parts)