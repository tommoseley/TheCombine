"""
Integration tests for Epic Backlog with Fragment Rendering (ADR-032).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.web.bff.epic_backlog_bff import get_epic_backlog_vm
from app.web.bff.fragment_renderer import FragmentRenderer


@pytest.fixture
def mock_db():
    """Create mock async session."""
    return AsyncMock()


@pytest.fixture
def mock_doc():
    """Create mock document with open questions."""
    doc = MagicMock()
    doc.id = uuid4()
    doc.updated_at = None
    doc.content = {
        "project_name": "Test Project",
        "epics": [
            {
                "epic_id": "E1",
                "name": "Epic One",
                "intent": "Test intent",
                "mvp_phase": "mvp",
                "open_questions": [
                    {
                        "id": "Q1",
                        "question": "What about X?",
                        "blocking_for_epic": True,
                        "why_it_matters": "Important for architecture",
                    },
                    {
                        "id": "Q2",
                        "question": "Should we use Y?",
                        "blocking_for_epic": False,
                    },
                ],
            },
        ],
    }
    return doc


@pytest.fixture
def mock_fragment_renderer():
    """Create mock fragment renderer."""
    renderer = AsyncMock(spec=FragmentRenderer)
    renderer.render_list.return_value = '<div class="open-question">Rendered Q1</div><div class="open-question">Rendered Q2</div>'
    return renderer


# =============================================================================
# Test: With Fragment Renderer
# =============================================================================

@pytest.mark.asyncio
async def test_epic_backlog_with_fragment_renderer(mock_db, mock_doc, mock_fragment_renderer):
    """BFF uses fragment renderer when provided."""
    project_id = uuid4()
    
    with patch("app.web.routes.public.document_routes._get_document_by_type") as mock_get_doc:
        mock_get_doc.return_value = mock_doc
        
        vm = await get_epic_backlog_vm(
            db=mock_db,
            project_id=project_id,
            project_name="Test Project",
            fragment_renderer=mock_fragment_renderer,
        )
    
    # Fragment renderer should have been called
    mock_fragment_renderer.render_list.assert_called_once()
    call_args = mock_fragment_renderer.render_list.call_args
    assert call_args[0][0] == "OpenQuestionV1"  # schema type
    assert len(call_args[0][1]) == 2  # 2 questions
    
    # Epic should have rendered content (per-epic, not backlog level)
    mvp_section = next(s for s in vm.sections if s.id == "mvp")
    assert len(mvp_section.epics) == 1
    assert mvp_section.epics[0].rendered_open_questions is not None
    assert "Rendered Q1" in mvp_section.epics[0].rendered_open_questions


@pytest.mark.asyncio
async def test_rendered_open_questions_contains_expected_html(mock_db, mock_doc, mock_fragment_renderer):
    """Rendered content is passed through to epic VM."""
    project_id = uuid4()
    expected_html = '<div class="test-fragment">Custom HTML</div>'
    mock_fragment_renderer.render_list.return_value = expected_html
    
    with patch("app.web.routes.public.document_routes._get_document_by_type") as mock_get_doc:
        mock_get_doc.return_value = mock_doc
        
        vm = await get_epic_backlog_vm(
            db=mock_db,
            project_id=project_id,
            project_name="Test Project",
            fragment_renderer=mock_fragment_renderer,
        )
    
    mvp_section = next(s for s in vm.sections if s.id == "mvp")
    assert mvp_section.epics[0].rendered_open_questions == expected_html


# =============================================================================
# Test: Without Fragment Renderer (Backward Compatibility)
# =============================================================================

@pytest.mark.asyncio
async def test_epic_backlog_without_fragment_renderer_unchanged(mock_db, mock_doc):
    """BFF works without fragment renderer (backward compatible)."""
    project_id = uuid4()
    
    with patch("app.web.routes.public.document_routes._get_document_by_type") as mock_get_doc:
        mock_get_doc.return_value = mock_doc
        
        vm = await get_epic_backlog_vm(
            db=mock_db,
            project_id=project_id,
            project_name="Test Project",
            # No fragment_renderer provided
        )
    
    # Should work without errors
    assert vm.exists is True
    
    # Epics should still be present
    assert len(vm.sections) == 2
    mvp_section = next(s for s in vm.sections if s.id == "mvp")
    assert len(mvp_section.epics) == 1
    assert len(mvp_section.epics[0].open_questions) == 2
    
    # No rendered content without renderer
    assert mvp_section.epics[0].rendered_open_questions is None


@pytest.mark.asyncio
async def test_epic_backlog_no_open_questions(mock_db, mock_fragment_renderer):
    """BFF handles epics without open questions gracefully."""
    project_id = uuid4()
    
    doc = MagicMock()
    doc.id = uuid4()
    doc.updated_at = None
    doc.content = {
        "epics": [
            {
                "epic_id": "E1",
                "name": "Epic Without Questions",
                "mvp_phase": "mvp",
                # No open_questions
            },
        ],
    }
    
    with patch("app.web.routes.public.document_routes._get_document_by_type") as mock_get_doc:
        mock_get_doc.return_value = doc
        
        vm = await get_epic_backlog_vm(
            db=mock_db,
            project_id=project_id,
            project_name="Test Project",
            fragment_renderer=mock_fragment_renderer,
        )
    
    # Should not call renderer if no questions
    mock_fragment_renderer.render_list.assert_not_called()
    
    mvp_section = next(s for s in vm.sections if s.id == "mvp")
    assert mvp_section.epics[0].rendered_open_questions is None


@pytest.mark.asyncio
async def test_epic_backlog_fragment_render_failure_graceful(mock_db, mock_doc):
    """BFF handles fragment render failure gracefully."""
    project_id = uuid4()
    
    failing_renderer = AsyncMock(spec=FragmentRenderer)
    failing_renderer.render_list.side_effect = Exception("Render failed")
    
    with patch("app.web.routes.public.document_routes._get_document_by_type") as mock_get_doc:
        mock_get_doc.return_value = mock_doc
        
        # Should not raise, should degrade gracefully
        vm = await get_epic_backlog_vm(
            db=mock_db,
            project_id=project_id,
            project_name="Test Project",
            fragment_renderer=failing_renderer,
        )
    
    # VM should still be valid
    assert vm.exists is True
    
    # Epic should exist but without rendered content (graceful degradation)
    mvp_section = next(s for s in vm.sections if s.id == "mvp")
    assert len(mvp_section.epics) == 1
    assert mvp_section.epics[0].rendered_open_questions is None