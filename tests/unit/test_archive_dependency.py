"""
Unit tests for verify_project_not_archived dependency.
"""

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies.archive import verify_project_not_archived


@pytest.mark.asyncio
async def test_dependency_allows_active_project():
    """Test that active projects pass through."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    project_id = "TEST-001"
    
    # Mock database response - project exists and is not archived
    # ORM returns tuple from .first() when selecting single column
    mock_result = MagicMock()
    mock_result.first.return_value = (None,)  # (archived_at,) - not archived
    db.execute.return_value = mock_result
    
    # Act - Should not raise
    await verify_project_not_archived(
        project_id=project_id,
        db=db
    )
    
    # Assert
    db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_dependency_blocks_archived_project():
    """Test that archived projects are blocked."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    project_id = "TEST-001"
    
    # Mock database response - project exists and IS archived
    from datetime import datetime, timezone
    mock_result = MagicMock()
    mock_result.first.return_value = (datetime.now(timezone.utc),)  # Archived!
    db.execute.return_value = mock_result
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await verify_project_not_archived(
            project_id=project_id,
            db=db
        )
    
    assert exc_info.value.status_code == 403
    assert "archived" in exc_info.value.detail.lower()
    assert "unarchive" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_dependency_handles_missing_project():
    """Test that missing projects return 404."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    fake_id = "FAKE-999"
    
    # Mock database response - project does NOT exist
    mock_result = MagicMock()
    mock_result.first.return_value = None  # Not found
    db.execute.return_value = mock_result
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await verify_project_not_archived(
            project_id=fake_id,
            db=db
        )
    
    assert exc_info.value.status_code == 404