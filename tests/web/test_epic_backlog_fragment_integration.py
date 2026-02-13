"""
Integration tests for Epic Backlog Fragment Rendering (ADR-033).

ADR-033: Fragment rendering is a web channel concern, not BFF.
BFF returns data-only contracts; templates invoke fragment rendering.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.web.bff.epic_backlog_bff import get_epic_backlog_vm


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


# =============================================================================
# Test: BFF Returns Data-Only Contracts (ADR-033)
# =============================================================================

@pytest.mark.asyncio
async def test_epic_backlog_bff_returns_data_only(mock_db, mock_doc):
    """BFF returns data-only contract with no HTML."""
    project_id = uuid4()
    
    with patch("app.web.routes.public.document_routes._get_document_by_type") as mock_get_doc:
        mock_get_doc.return_value = mock_doc
        
        vm = await get_epic_backlog_vm(
            db=mock_db,
            project_id=project_id,
            project_name="Test Project",
        )
    
    # Should have data
    assert vm.exists is True
    
    # Epics should have open_questions as data (not HTML)
    mvp_section = next(s for s in vm.sections if s.id == "mvp")
    assert len(mvp_section.epics) == 1
    epic = mvp_section.epics[0]
    
    # open_questions is a list of OpenQuestionVM (data)
    assert len(epic.open_questions) == 2
    assert epic.open_questions[0].question == "What about X?"
    assert epic.open_questions[0].blocking is True
    assert epic.open_questions[1].question == "Should we use Y?"
    assert epic.open_questions[1].blocking is False


@pytest.mark.asyncio
async def test_epic_backlog_bff_no_fragment_renderer_param(mock_db, mock_doc):
    """BFF does not accept fragment_renderer parameter (ADR-033)."""
    import inspect
    sig = inspect.signature(get_epic_backlog_vm)
    param_names = list(sig.parameters.keys())
    
    # fragment_renderer should NOT be a parameter
    assert "fragment_renderer" not in param_names


@pytest.mark.asyncio
async def test_epic_card_vm_no_rendered_field(mock_db, mock_doc):
    """EpicCardVM has no rendered_open_questions field (ADR-033)."""
    from app.web.viewmodels.epic_backlog_vm import EpicCardVM
    
    # Check model fields
    field_names = list(EpicCardVM.model_fields.keys())
    assert "rendered_open_questions" not in field_names


# =============================================================================
# Test: Open Questions Data Structure
# =============================================================================

@pytest.mark.asyncio
async def test_open_questions_mapped_correctly(mock_db, mock_doc):
    """Open questions are mapped to OpenQuestionVM correctly."""
    project_id = uuid4()
    
    with patch("app.web.routes.public.document_routes._get_document_by_type") as mock_get_doc:
        mock_get_doc.return_value = mock_doc
        
        vm = await get_epic_backlog_vm(
            db=mock_db,
            project_id=project_id,
            project_name="Test Project",
        )
    
    mvp_section = next(s for s in vm.sections if s.id == "mvp")
    epic = mvp_section.epics[0]
    
    # First question (blocking)
    q1 = epic.open_questions[0]
    assert q1.question == "What about X?"
    assert q1.blocking is True
    
    # Second question (not blocking)
    q2 = epic.open_questions[1]
    assert q2.question == "Should we use Y?"
    assert q2.blocking is False


@pytest.mark.asyncio
async def test_epic_without_open_questions(mock_db):
    """Epic without open_questions has empty list."""
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
                # No open_questions key
            },
        ],
    }
    
    with patch("app.web.routes.public.document_routes._get_document_by_type") as mock_get_doc:
        mock_get_doc.return_value = doc
        
        vm = await get_epic_backlog_vm(
            db=mock_db,
            project_id=project_id,
            project_name="Test Project",
        )
    
    mvp_section = next(s for s in vm.sections if s.id == "mvp")
    assert len(mvp_section.epics[0].open_questions) == 0


# =============================================================================
# Test: Template Helpers (PreloadedFragmentRenderer)
# =============================================================================

def test_preloaded_fragment_renderer_render():
    """PreloadedFragmentRenderer.render returns Markup."""
    from app.web.template_helpers import PreloadedFragmentRenderer
    from markupsafe import Markup
    
    # Provide a simple template
    templates = {"TestType": "<div>{{ item.name }}</div>"}
    renderer = PreloadedFragmentRenderer(templates)
    
    result = renderer.render("TestType", {"name": "Hello"})
    
    assert isinstance(result, Markup)
    assert "<div>Hello</div>" in str(result)


def test_preloaded_fragment_renderer_render_list():
    """PreloadedFragmentRenderer.render_list returns Markup."""
    from app.web.template_helpers import PreloadedFragmentRenderer
    from markupsafe import Markup
    
    templates = {"TestType": "<span>{{ item.val }}</span>"}
    renderer = PreloadedFragmentRenderer(templates)
    
    result = renderer.render_list("TestType", [{"val": "A"}, {"val": "B"}])
    
    assert isinstance(result, Markup)
    assert "<span>A</span>" in str(result)
    assert "<span>B</span>" in str(result)


def test_preloaded_fragment_renderer_missing_template():
    """PreloadedFragmentRenderer returns empty Markup for missing template."""
    from app.web.template_helpers import PreloadedFragmentRenderer
    from markupsafe import Markup
    
    templates = {}  # No templates
    renderer = PreloadedFragmentRenderer(templates)
    
    result = renderer.render("MissingType", {"key": "value"})
    
    assert isinstance(result, Markup)
    assert str(result) == ""


def test_preloaded_fragment_renderer_graceful_failure():
    """PreloadedFragmentRenderer returns empty Markup on render failure."""
    from app.web.template_helpers import PreloadedFragmentRenderer
    from markupsafe import Markup
    
    # Template that references undefined variable
    templates = {"BadType": "{{ item.undefined_var.nested }}"}
    renderer = PreloadedFragmentRenderer(templates)
    
    result = renderer.render("BadType", {})
    
    assert isinstance(result, Markup)
    assert str(result) == ""