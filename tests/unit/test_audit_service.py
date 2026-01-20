"""
Unit tests for ProjectAuditService (ORM version).
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_service import audit_service


@pytest.mark.asyncio
async def test_log_event_creates_audit_entry():
    """Test basic audit event creation via ORM."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    project_id = uuid4()
    user_id = uuid4()
    
    # Act
    await audit_service.log_event(
        db=db,
        project_id=project_id,
        action='CREATED',
        actor_user_id=user_id,
        metadata={'test': True}
    )
    
    # Assert - ORM uses db.add()
    db.add.assert_called_once()
    audit_entry = db.add.call_args[0][0]
    
    assert audit_entry.project_id == project_id
    assert audit_entry.actor_user_id == user_id
    assert audit_entry.action == 'CREATED'
    assert audit_entry.meta['test'] == True


@pytest.mark.asyncio
async def test_log_event_rejects_invalid_action():
    """Test action validation."""
    db = AsyncMock(spec=AsyncSession)
    
    with pytest.raises(ValueError, match="Invalid audit action"):
        await audit_service.log_event(
            db=db,
            project_id=uuid4(),
            action='INVALID_ACTION',
            actor_user_id=uuid4()
        )
    
    # Should not add anything if validation fails
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_log_event_adds_meta_version():
    """Test metadata auto-enrichment."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    project_id = uuid4()
    
    # Act
    await audit_service.log_event(
        db=db,
        project_id=project_id,
        action='UPDATED',
        actor_user_id=uuid4(),
        metadata={'changed_fields': ['name']}
    )
    
    # Assert
    audit_entry = db.add.call_args[0][0]
    
    assert audit_entry.meta['meta_version'] == '1.0'
    assert audit_entry.meta['changed_fields'] == ['name']


@pytest.mark.asyncio
async def test_log_event_with_correlation_id():
    """Test correlation ID is added to metadata."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    project_id = uuid4()
    correlation_id = str(uuid4())
    
    # Act
    await audit_service.log_event(
        db=db,
        project_id=project_id,
        action='ARCHIVED',
        actor_user_id=uuid4(),
        reason='Testing',
        correlation_id=correlation_id
    )
    
    # Assert
    audit_entry = db.add.call_args[0][0]
    
    assert audit_entry.meta['correlation_id'] == correlation_id
    assert audit_entry.reason == 'Testing'


@pytest.mark.asyncio
async def test_log_event_with_null_actor():
    """Test system actions with NULL actor_user_id."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    project_id = uuid4()
    
    # Act
    await audit_service.log_event(
        db=db,
        project_id=project_id,
        action='CREATED',
        actor_user_id=None,  # System action
        metadata={
            'actor_type': 'system',
            'actor_name': 'migration'
        }
    )
    
    # Assert
    audit_entry = db.add.call_args[0][0]
    
    assert audit_entry.actor_user_id is None
    assert audit_entry.meta['actor_type'] == 'system'