"""
Unit tests for ProjectAuditService.
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.core.audit_service import audit_service


@pytest.mark.asyncio
async def test_log_event_creates_audit_entry():
    """Test basic audit event creation."""
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
    
    # Assert
    db.execute.assert_called_once()
    call_args = db.execute.call_args
    
    # call_args[0] is the positional args tuple: (query, params)
    query = str(call_args[0][0])  # The SQL query
    params = call_args[0][1]       # The parameters dict
    
    assert 'INSERT INTO project_audit' in query
    assert params['project_id'] == str(project_id)
    assert params['actor_user_id'] == str(user_id)
    assert params['action'] == 'CREATED'


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
    call_args = db.execute.call_args
    params = call_args[0][1]
    metadata = json.loads(params['metadata'])
    
    assert metadata['meta_version'] == '1.0'
    assert metadata['changed_fields'] == ['name']


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
    call_args = db.execute.call_args
    params = call_args[0][1]
    metadata = json.loads(params['metadata'])
    
    assert metadata['correlation_id'] == correlation_id
    assert params['reason'] == 'Testing'


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
    call_args = db.execute.call_args
    params = call_args[0][1]
    
    assert params['actor_user_id'] is None
    
    metadata = json.loads(params['metadata'])
    assert metadata['actor_type'] == 'system'