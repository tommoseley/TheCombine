"""
Tests for Epic Backlog BFF function.

Per ADR-030 and WS-001: Verify BFF returns correct ViewModels.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from app.web.viewmodels import (
    EpicBacklogVM,
    EpicBacklogSectionVM,
    EpicCardVM,
    OpenQuestionVM,
    DependencyVM,
)
from app.web.bff.epic_backlog_bff import (
    get_epic_backlog_vm,
    _map_epic_to_card_vm,
    _empty_sections,
    _format_dt,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def project_id():
    return uuid4()


@pytest.fixture
def mock_document():
    """Mock Document with content."""
    doc = MagicMock()
    doc.id = uuid4()
    doc.updated_at = datetime(2026, 1, 6, 12, 0, 0)
    doc.content = {
        "project_name": "Test Project",
        "epics": [
            {
                "epic_id": "EPIC-001",
                "name": "MVP Epic",
                "intent": "Build core functionality",
                "mvp_phase": "mvp",
                "business_value": "High value",
                "in_scope": ["Feature A", "Feature B"],
                "out_of_scope": ["Feature C"],
                "primary_outcomes": ["Outcome 1"],
                "open_questions": [
                    {"question": "Blocking question?", "blocking_for_epic": True, "directed_to": "architect"},
                    {"question": "Non-blocking?", "blocking_for_epic": False},
                ],
                "dependencies": [
                    {"depends_on_epic_id": "EPIC-000", "reason": "Needs foundation"},
                ],
                "architecture_attention_points": ["Consider scaling"],
                "related_discovery_items": {
                    "risks": ["Risk 1"],
                    "unknowns": ["Unknown 1"],
                    "early_decision_points": ["Decision 1"],
                },
            },
            {
                "epic_id": "EPIC-002",
                "name": "Later Epic",
                "intent": "Future work",
                "mvp_phase": "later-phase",
            },
        ],
        "epic_set_summary": {
            "overall_intent": "Build the system",
            "mvp_definition": "Core features only",
            "key_constraints": ["Time", "Budget"],
            "out_of_scope": ["Phase 2 features"],
        },
        "risks_overview": [
            {"description": "Technical risk", "impact": "High", "affected_epics": ["EPIC-001"]},
        ],
        "recommendations_for_architecture": ["Use microservices"],
    }
    return doc


# =============================================================================
# Test: Happy Path
# =============================================================================

@pytest.mark.asyncio
async def test_get_epic_backlog_vm_with_document(project_id, mock_document):
    """Test BFF returns correct VM when document exists."""
    mock_db = AsyncMock()
    
    with patch(
        "app.web.routes.public.document_routes._get_document_by_type",
        new_callable=AsyncMock,
        return_value=mock_document,
    ):
        vm = await get_epic_backlog_vm(
            db=mock_db,
            project_id=project_id,
            project_name="Test Project",
            base_url="",
        )
    
    assert vm.exists is True
    assert vm.project_name == "Test Project"
    assert vm.document_id is not None
    assert len(vm.sections) == 2
    
    # Check MVP section
    mvp_section = vm.sections[0]
    assert mvp_section.id == "mvp"
    assert len(mvp_section.epics) == 1
    assert mvp_section.epics[0].epic_id == "EPIC-001"
    
    # Check Later section
    later_section = vm.sections[1]
    assert later_section.id == "later"
    assert len(later_section.epics) == 1
    assert later_section.epics[0].epic_id == "EPIC-002"


# =============================================================================
# Test: Empty State
# =============================================================================

@pytest.mark.asyncio
async def test_get_epic_backlog_vm_no_document(project_id):
    """Test BFF returns exists=False when document not found."""
    mock_db = AsyncMock()
    
    with patch(
        "app.web.routes.public.document_routes._get_document_by_type",
        new_callable=AsyncMock,
        return_value=None,
    ):
        vm = await get_epic_backlog_vm(
            db=mock_db,
            project_id=project_id,
            project_name="Test Project",
            base_url="",
        )
    
    assert vm.exists is False
    assert vm.message is not None
    assert len(vm.sections) == 2  # Empty sections still provided


# =============================================================================
# Test: Epic Classification
# =============================================================================

def test_epic_classification_mvp(project_id):
    """Test epics with mvp_phase='mvp' are classified correctly."""
    epic = {"epic_id": "E1", "name": "Test", "mvp_phase": "mvp"}
    card = _map_epic_to_card_vm(epic, project_id, "")
    assert card.mvp_phase == "mvp"


def test_epic_classification_later(project_id):
    """Test epics with mvp_phase='later-phase' are classified as later."""
    epic = {"epic_id": "E1", "name": "Test", "mvp_phase": "later-phase"}
    card = _map_epic_to_card_vm(epic, project_id, "")
    assert card.mvp_phase == "later"


def test_epic_classification_default(project_id):
    """Test epics without mvp_phase default to later."""
    epic = {"epic_id": "E1", "name": "Test"}
    card = _map_epic_to_card_vm(epic, project_id, "")
    assert card.mvp_phase == "later"


# =============================================================================
# Test: Open Questions Mapping
# =============================================================================

def test_open_questions_mapping_blocking(project_id):
    """Test blocking flag maps correctly from blocking_for_epic."""
    epic = {
        "epic_id": "E1",
        "name": "Test",
        "open_questions": [
            {"question": "Q1", "blocking_for_epic": True},
            {"question": "Q2", "blocking_for_epic": False},
        ],
    }
    card = _map_epic_to_card_vm(epic, project_id, "")
    
    assert len(card.open_questions) == 2
    assert card.open_questions[0].question == "Q1"
    assert card.open_questions[0].blocking is True
    assert card.open_questions[1].question == "Q2"
    assert card.open_questions[1].blocking is False


# =============================================================================
# Test: Dependencies Mapping
# =============================================================================

def test_dependencies_mapping(project_id):
    """Test dependencies map correctly."""
    epic = {
        "epic_id": "E1",
        "name": "Test",
        "dependencies": [
            {"depends_on_epic_id": "E0", "reason": "Foundation needed"},
        ],
    }
    card = _map_epic_to_card_vm(epic, project_id, "")
    
    assert len(card.dependencies) == 1
    assert card.dependencies[0].depends_on_epic_id == "E0"
    assert card.dependencies[0].reason == "Foundation needed"


# =============================================================================
# Test: Missing Fields Handled
# =============================================================================

def test_missing_fields_handled(project_id):
    """Test missing JSON fields don't cause errors."""
    epic = {"epic_id": "E1"}  # Minimal epic
    card = _map_epic_to_card_vm(epic, project_id, "")
    
    assert card.epic_id == "E1"
    assert card.name == "Untitled Epic"
    assert card.intent == ""
    assert card.in_scope == []
    assert card.open_questions == []
    assert card.dependencies == []


# =============================================================================
# Test: Helper Functions
# =============================================================================

def test_empty_sections():
    """Test _empty_sections returns correct structure."""
    sections = _empty_sections()
    assert len(sections) == 2
    assert sections[0].id == "mvp"
    assert sections[1].id == "later"
    assert sections[0].epics == []


def test_format_dt_with_value():
    """Test datetime formatting."""
    dt = datetime(2026, 1, 6, 14, 30, 0)
    result = _format_dt(dt)
    assert "Jan" in result
    assert "06" in result
    assert "2026" in result


def test_format_dt_none():
    """Test None datetime returns None."""
    assert _format_dt(None) is None

# =============================================================================
# Test: EpicSetSummary Mapping
# =============================================================================

@pytest.mark.asyncio
async def test_epic_set_summary_mapping(project_id):
    """Test epic_set_summary maps all fields correctly."""
    mock_db = AsyncMock()
    mock_doc = MagicMock()
    mock_doc.id = uuid4()
    mock_doc.updated_at = datetime(2026, 1, 6, 12, 0, 0)
    mock_doc.content = {
        "epics": [],
        "epic_set_summary": {
            "overall_intent": "Build the system",
            "mvp_definition": "Core features",
            "key_constraints": ["Time", "Budget"],
            "out_of_scope": ["Phase 2"],
        },
    }
    
    with patch(
        "app.web.routes.public.document_routes._get_document_by_type",
        new_callable=AsyncMock,
        return_value=mock_doc,
    ):
        vm = await get_epic_backlog_vm(
            db=mock_db,
            project_id=project_id,
            project_name="Test",
            base_url="",
        )
    
    assert vm.epic_set_summary is not None
    assert vm.epic_set_summary.overall_intent == "Build the system"
    assert vm.epic_set_summary.mvp_definition == "Core features"
    assert vm.epic_set_summary.key_constraints == ["Time", "Budget"]
    assert vm.epic_set_summary.out_of_scope == ["Phase 2"]


@pytest.mark.asyncio
async def test_epic_set_summary_missing(project_id):
    """Test missing epic_set_summary returns None."""
    mock_db = AsyncMock()
    mock_doc = MagicMock()
    mock_doc.id = uuid4()
    mock_doc.updated_at = None
    mock_doc.content = {"epics": []}
    
    with patch(
        "app.web.routes.public.document_routes._get_document_by_type",
        new_callable=AsyncMock,
        return_value=mock_doc,
    ):
        vm = await get_epic_backlog_vm(
            db=mock_db,
            project_id=project_id,
            project_name="Test",
            base_url="",
        )
    
    assert vm.epic_set_summary is None


# =============================================================================
# Test: Risks Overview Mapping
# =============================================================================

@pytest.mark.asyncio
async def test_risks_overview_mapping(project_id):
    """Test risks_overview maps correctly."""
    mock_db = AsyncMock()
    mock_doc = MagicMock()
    mock_doc.id = uuid4()
    mock_doc.updated_at = None
    mock_doc.content = {
        "epics": [],
        "risks_overview": [
            {"description": "Risk 1", "impact": "High", "affected_epics": ["E1", "E2"]},
            {"description": "Risk 2", "impact": "Low", "affected_epics": []},
        ],
    }
    
    with patch(
        "app.web.routes.public.document_routes._get_document_by_type",
        new_callable=AsyncMock,
        return_value=mock_doc,
    ):
        vm = await get_epic_backlog_vm(
            db=mock_db,
            project_id=project_id,
            project_name="Test",
            base_url="",
        )
    
    assert len(vm.risks_overview) == 2
    assert vm.risks_overview[0].description == "Risk 1"
    assert vm.risks_overview[0].impact == "High"
    assert vm.risks_overview[0].affected_epics == ["E1", "E2"]


# =============================================================================
# Test: Related Discovery Items Mapping
# =============================================================================

def test_related_discovery_items_mapping(project_id):
    """Test related_discovery_items maps correctly."""
    epic = {
        "epic_id": "E1",
        "name": "Test",
        "related_discovery_items": {
            "risks": ["Risk A", "Risk B"],
            "unknowns": ["Unknown X"],
            "early_decision_points": ["Decision 1"],
        },
    }
    card = _map_epic_to_card_vm(epic, project_id, "")
    
    assert card.related_discovery_items is not None
    assert card.related_discovery_items.risks == ["Risk A", "Risk B"]
    assert card.related_discovery_items.unknowns == ["Unknown X"]
    assert card.related_discovery_items.early_decision_points == ["Decision 1"]


def test_related_discovery_items_missing(project_id):
    """Test missing related_discovery_items returns None."""
    epic = {"epic_id": "E1", "name": "Test"}
    card = _map_epic_to_card_vm(epic, project_id, "")
    assert card.related_discovery_items is None


# =============================================================================
# Test: Recommendations Mapping
# =============================================================================

@pytest.mark.asyncio
async def test_recommendations_mapping(project_id):
    """Test recommendations_for_architecture maps correctly."""
    mock_db = AsyncMock()
    mock_doc = MagicMock()
    mock_doc.id = uuid4()
    mock_doc.updated_at = None
    mock_doc.content = {
        "epics": [],
        "recommendations_for_architecture": ["Use microservices", "Add caching"],
    }
    
    with patch(
        "app.web.routes.public.document_routes._get_document_by_type",
        new_callable=AsyncMock,
        return_value=mock_doc,
    ):
        vm = await get_epic_backlog_vm(
            db=mock_db,
            project_id=project_id,
            project_name="Test",
            base_url="",
        )
    
    assert vm.recommendations_for_architecture == ["Use microservices", "Add caching"]


# =============================================================================
# Test: Malformed Data Handling
# =============================================================================

def test_malformed_open_questions_string_instead_of_dict(project_id):
    """Test open_questions handles string items gracefully."""
    epic = {
        "epic_id": "E1",
        "name": "Test",
        "open_questions": ["Simple string question", {"question": "Dict question"}],
    }
    card = _map_epic_to_card_vm(epic, project_id, "")
    
    assert len(card.open_questions) == 2
    assert card.open_questions[0].question == "Simple string question"
    assert card.open_questions[0].blocking is False
    assert card.open_questions[1].question == "Dict question"


def test_malformed_dependencies_string_instead_of_dict(project_id):
    """Test dependencies handles string items gracefully."""
    epic = {
        "epic_id": "E1",
        "name": "Test",
        "dependencies": ["E0", {"depends_on_epic_id": "E2", "reason": "Needs E2"}],
    }
    card = _map_epic_to_card_vm(epic, project_id, "")
    
    assert len(card.dependencies) == 2
    assert card.dependencies[0].depends_on_epic_id == "E0"
    assert card.dependencies[0].reason == ""
    assert card.dependencies[1].depends_on_epic_id == "E2"


# =============================================================================
# Test: ViewModel Computed Properties
# =============================================================================

def test_epic_backlog_vm_mvp_count():
    """Test mvp_count computed property."""
    vm = EpicBacklogVM(
        sections=[
            EpicBacklogSectionVM(id="mvp", title="MVP", epics=[
                EpicCardVM(epic_id="E1"),
                EpicCardVM(epic_id="E2"),
            ]),
            EpicBacklogSectionVM(id="later", title="Later", epics=[
                EpicCardVM(epic_id="E3"),
            ]),
        ]
    )
    assert vm.mvp_count == 2
    assert vm.later_count == 1


def test_section_count_property():
    """Test EpicBacklogSectionVM.count property."""
    section = EpicBacklogSectionVM(
        id="mvp",
        title="MVP",
        epics=[EpicCardVM(epic_id="E1"), EpicCardVM(epic_id="E2")],
    )
    assert section.count == 2