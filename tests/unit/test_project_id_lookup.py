"""
Tests for project route UUID/string ID handling.

Bug: GET /projects/{uuid} returns 404 because _get_project_with_icon
queries Project.project_id (string like "ABC-001") instead of Project.id (UUID).
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.web.routes.public.project_routes import _get_project_with_icon


class TestProjectIdLookup:
    """Test that project lookup handles both UUID and string IDs."""
    
    @pytest.mark.asyncio
    async def test_get_project_by_uuid_queries_id_column(self):
        """
        BUG REPRODUCTION: When URL contains UUID (id column value),
        _get_project_with_icon should query the id column, not project_id.
        
        Currently fails because it queries project_id column (string)
        instead of id column (UUID).
        """
        # Arrange
        db = AsyncMock(spec=AsyncSession)
        mock_user = MagicMock()
        mock_user.id = uuid4()
        
        project_uuid = uuid4()
        project_uuid_str = str(project_uuid)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result
        
        # Act - pass UUID string (as comes from URL like /projects/28589b0a-...)
        await _get_project_with_icon(db, project_uuid_str, mock_user)
        
        # Assert - verify the WHERE clause uses the correct column
        call_args = db.execute.call_args
        query = call_args[0][0]
        query_str = str(query.compile(compile_kwargs={"literal_binds": True}))
        
        # Extract WHERE clause for precise check
        where_clause = query_str.split("WHERE")[1] if "WHERE" in query_str else ""
        
        # UUID input should query projects.id, not projects.project_id
        assert f"projects.id = '{project_uuid_str}'" in where_clause or \
               "projects.id =" in where_clause, \
            f"WHERE clause should use 'projects.id' for UUID input. Got: WHERE{where_clause}"
    
    @pytest.mark.asyncio
    async def test_get_project_by_string_id_queries_project_id_column(self):
        """String project_id (like 'ABC-001') should query project_id column."""
        # Arrange
        db = AsyncMock(spec=AsyncSession)
        mock_user = MagicMock()
        mock_user.id = uuid4()
        
        string_project_id = "TEST-001"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result
        
        # Act - pass string ID (like ABC-001)
        await _get_project_with_icon(db, string_project_id, mock_user)
        
        # Assert - verify the WHERE clause uses the correct column
        call_args = db.execute.call_args
        query = call_args[0][0]
        query_str = str(query.compile(compile_kwargs={"literal_binds": True}))
        
        # Extract WHERE clause
        where_clause = query_str.split("WHERE")[1] if "WHERE" in query_str else ""
        
        # String IDs should query project_id column
        assert f"projects.project_id = '{string_project_id}'" in where_clause, \
            f"WHERE clause should use 'projects.project_id' for string input. Got: WHERE{where_clause}"