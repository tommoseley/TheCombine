"""
Test Suite for DocumentStatusService - ADR-007 Implementation

Tests all status combinations for sidebar document visualization:
- Readiness: ready, stale, blocked, waiting
- Acceptance: accepted, needs_acceptance, rejected, None

Each combination is tested for correct derivation and UI implications.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.services.document_status_service import (
    DocumentStatusService,
    DocumentStatus,
    ReadinessStatus,
    AcceptanceState,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def status_service():
    """Create a fresh DocumentStatusService instance."""
    return DocumentStatusService()


@pytest.fixture
def mock_doc_type_no_acceptance():
    """Document type that doesn't require acceptance."""
    doc_type = MagicMock()
    doc_type.doc_type_id = "project_discovery"
    doc_type.name = "Product Discovery"
    doc_type.icon = "search"
    doc_type.acceptance_required = False
    doc_type.accepted_by_role = None
    doc_type.required_inputs = []
    doc_type.display_order = 1
    return doc_type


@pytest.fixture
def mock_doc_type_with_acceptance():
    """Document type that requires acceptance."""
    doc_type = MagicMock()
    doc_type.doc_type_id = "architecture_spec"
    doc_type.name = "Technical Architecture"
    doc_type.icon = "landmark"
    doc_type.acceptance_required = True
    doc_type.accepted_by_role = "architect"
    doc_type.required_inputs = ["project_discovery"]
    doc_type.display_order = 2
    return doc_type


@pytest.fixture
def mock_doc_type_blocked():
    """Document type with multiple dependencies."""
    doc_type = MagicMock()
    doc_type.doc_type_id = "story_backlog"
    doc_type.name = "Story Backlog"
    doc_type.icon = "list-checks"
    doc_type.acceptance_required = False
    doc_type.accepted_by_role = None
    doc_type.required_inputs = ["project_discovery", "architecture_spec", "epic_set"]
    doc_type.display_order = 3
    return doc_type


def make_document(
    doc_type_id: str,
    is_stale: bool = False,
    accepted_at: datetime = None,
    rejected_at: datetime = None,
    accepted_by: str = None,
    rejected_by: str = None,
    rejection_reason: str = None,
):
    """Factory for creating mock Document objects."""
    doc = MagicMock()
    doc.id = uuid4()
    doc.doc_type_id = doc_type_id
    doc.is_stale = is_stale
    doc.accepted_at = accepted_at
    doc.accepted_by = accepted_by
    doc.rejected_at = rejected_at
    doc.rejected_by = rejected_by
    doc.rejection_reason = rejection_reason
    return doc


# =============================================================================
# READINESS STATUS DERIVATION TESTS
# =============================================================================

class TestReadinessDerivation:
    """Test readiness status derivation logic."""

    def test_ready_when_document_exists_and_current(
        self, status_service, mock_doc_type_no_acceptance
    ):
        """Document exists and is not stale → ready."""
        document = make_document("project_discovery", is_stale=False)
        existing_type_ids = {"project_discovery"}
        
        readiness, missing = status_service._derive_readiness(
            doc_type=mock_doc_type_no_acceptance,
            document=document,
            existing_type_ids=existing_type_ids,
        )
        
        assert readiness == ReadinessStatus.PRODUCED
        assert missing == []

    def test_stale_when_document_marked_stale(
        self, status_service, mock_doc_type_no_acceptance
    ):
        """Document exists but is_stale=True → stale."""
        document = make_document("project_discovery", is_stale=True)
        existing_type_ids = {"project_discovery"}
        
        readiness, missing = status_service._derive_readiness(
            doc_type=mock_doc_type_no_acceptance,
            document=document,
            existing_type_ids=existing_type_ids,
        )
        
        assert readiness == ReadinessStatus.STALE
        assert missing == []

    def test_waiting_when_no_document_but_deps_met(
        self, status_service, mock_doc_type_with_acceptance
    ):
        """No document exists, but all required inputs exist → waiting."""
        existing_type_ids = {"project_discovery"}  # The required input exists
        
        readiness, missing = status_service._derive_readiness(
            doc_type=mock_doc_type_with_acceptance,
            document=None,
            existing_type_ids=existing_type_ids,
        )
        
        assert readiness == ReadinessStatus.READY_FOR_PRODUCTION
        assert missing == []

    def test_waiting_when_no_deps_required(
        self, status_service, mock_doc_type_no_acceptance
    ):
        """No document, no dependencies required → waiting."""
        readiness, missing = status_service._derive_readiness(
            doc_type=mock_doc_type_no_acceptance,
            document=None,
            existing_type_ids=set(),
        )
        
        assert readiness == ReadinessStatus.READY_FOR_PRODUCTION
        assert missing == []

    def test_blocked_when_missing_single_dependency(
        self, status_service, mock_doc_type_with_acceptance
    ):
        """Missing required input → blocked."""
        existing_type_ids = set()  # project_discovery is missing
        
        readiness, missing = status_service._derive_readiness(
            doc_type=mock_doc_type_with_acceptance,
            document=None,
            existing_type_ids=existing_type_ids,
        )
        
        assert readiness == ReadinessStatus.REQUIREMENTS_NOT_MET
        assert missing == ["project_discovery"]

    def test_blocked_when_missing_multiple_dependencies(
        self, status_service, mock_doc_type_blocked
    ):
        """Missing multiple required inputs → blocked with all missing listed."""
        existing_type_ids = {"project_discovery"}  # Only one of three exists
        
        readiness, missing = status_service._derive_readiness(
            doc_type=mock_doc_type_blocked,
            document=None,
            existing_type_ids=existing_type_ids,
        )
        
        assert readiness == ReadinessStatus.REQUIREMENTS_NOT_MET
        assert set(missing) == {"architecture_spec", "epic_set"}

    def test_blocked_takes_precedence_over_stale(
        self, status_service, mock_doc_type_with_acceptance
    ):
        """Even if document exists and is stale, missing deps → blocked."""
        # This is an edge case - document exists but deps are missing
        # (could happen if a dependency was deleted)
        document = make_document("architecture_spec", is_stale=True)
        existing_type_ids = set()  # project_discovery was deleted!
        
        readiness, missing = status_service._derive_readiness(
            doc_type=mock_doc_type_with_acceptance,
            document=document,
            existing_type_ids=existing_type_ids,
        )
        
        assert readiness == ReadinessStatus.REQUIREMENTS_NOT_MET
        assert missing == ["project_discovery"]


# =============================================================================
# ACCEPTANCE STATE DERIVATION TESTS
# =============================================================================

class TestAcceptanceDerivation:
    """Test acceptance state derivation logic."""

    def test_none_when_acceptance_not_required(
        self, status_service, mock_doc_type_no_acceptance
    ):
        """acceptance_required=False → None regardless of document state."""
        document = make_document("project_discovery")
        
        acceptance = status_service._derive_acceptance_state(
            doc_type=mock_doc_type_no_acceptance,
            document=document,
        )
        
        assert acceptance is None

    def test_none_when_document_does_not_exist(
        self, status_service, mock_doc_type_with_acceptance
    ):
        """Can't accept what doesn't exist → None."""
        acceptance = status_service._derive_acceptance_state(
            doc_type=mock_doc_type_with_acceptance,
            document=None,
        )
        
        assert acceptance is None

    def test_needs_acceptance_when_not_accepted(
        self, status_service, mock_doc_type_with_acceptance
    ):
        """Document exists, acceptance required, not yet accepted → needs_acceptance."""
        document = make_document("architecture_spec")
        
        acceptance = status_service._derive_acceptance_state(
            doc_type=mock_doc_type_with_acceptance,
            document=document,
        )
        
        assert acceptance == AcceptanceState.NEEDS_ACCEPTANCE

    def test_accepted_when_accepted_at_set(
        self, status_service, mock_doc_type_with_acceptance
    ):
        """Document accepted → accepted."""
        document = make_document(
            "architecture_spec",
            accepted_at=datetime.now(timezone.utc),
            accepted_by="architect@example.com",
        )
        
        acceptance = status_service._derive_acceptance_state(
            doc_type=mock_doc_type_with_acceptance,
            document=document,
        )
        
        assert acceptance == AcceptanceState.ACCEPTED

    def test_rejected_when_rejected_at_set(
        self, status_service, mock_doc_type_with_acceptance
    ):
        """Document rejected → rejected."""
        document = make_document(
            "architecture_spec",
            rejected_at=datetime.now(timezone.utc),
            rejected_by="architect@example.com",
            rejection_reason="Missing error handling",
        )
        
        acceptance = status_service._derive_acceptance_state(
            doc_type=mock_doc_type_with_acceptance,
            document=document,
        )
        
        assert acceptance == AcceptanceState.REJECTED

    def test_rejected_takes_precedence_over_accepted(
        self, status_service, mock_doc_type_with_acceptance
    ):
        """If both accepted_at and rejected_at set, rejection wins."""
        # Edge case: document was accepted, then rejected
        document = make_document(
            "architecture_spec",
            accepted_at=datetime.now(timezone.utc),
            accepted_by="architect@example.com",
            rejected_at=datetime.now(timezone.utc),
            rejected_by="pm@example.com",
        )
        
        acceptance = status_service._derive_acceptance_state(
            doc_type=mock_doc_type_with_acceptance,
            document=document,
        )
        
        assert acceptance == AcceptanceState.REJECTED


# =============================================================================
# SUBTITLE DERIVATION TESTS
# =============================================================================

class TestSubtitleDerivation:
    """Test contextual subtitle generation."""

    def test_blocked_shows_missing_dependencies(
        self, status_service, mock_doc_type_blocked
    ):
        """Blocked state shows what's missing."""
        subtitle = status_service._derive_subtitle(
            doc_type=mock_doc_type_blocked,
            document=None,
            readiness=ReadinessStatus.REQUIREMENTS_NOT_MET,
            acceptance_state=None,
            missing_inputs=["architecture_spec", "epic_set"],
        )
        
        assert "Missing:" in subtitle
        assert "architecture_spec" in subtitle
        assert "epic_set" in subtitle

    def test_stale_accepted_shows_review_warning(
        self, status_service, mock_doc_type_with_acceptance
    ):
        """Stale + accepted shows review recommendation (ADR-007 UI Rule)."""
        subtitle = status_service._derive_subtitle(
            doc_type=mock_doc_type_with_acceptance,
            document=MagicMock(),
            readiness=ReadinessStatus.STALE,
            acceptance_state=AcceptanceState.ACCEPTED,
            missing_inputs=[],
        )
        
        assert "review recommended" in subtitle.lower()

    def test_needs_acceptance_shows_role(
        self, status_service, mock_doc_type_with_acceptance
    ):
        """Needs acceptance shows responsible role."""
        subtitle = status_service._derive_subtitle(
            doc_type=mock_doc_type_with_acceptance,
            document=MagicMock(),
            readiness=ReadinessStatus.PRODUCED,
            acceptance_state=AcceptanceState.NEEDS_ACCEPTANCE,
            missing_inputs=[],
        )
        
        assert "acceptance" in subtitle.lower()
        assert "Architect" in subtitle  # Role capitalized

    def test_rejected_shows_changes_requested(
        self, status_service, mock_doc_type_with_acceptance
    ):
        """Rejected state shows changes requested."""
        subtitle = status_service._derive_subtitle(
            doc_type=mock_doc_type_with_acceptance,
            document=MagicMock(),
            readiness=ReadinessStatus.PRODUCED,
            acceptance_state=AcceptanceState.REJECTED,
            missing_inputs=[],
        )
        
        assert "changes requested" in subtitle.lower()

    def test_waiting_with_acceptance_shows_future_hint(
        self, status_service, mock_doc_type_with_acceptance
    ):
        """Waiting + acceptance required hints about future acceptance."""
        subtitle = status_service._derive_subtitle(
            doc_type=mock_doc_type_with_acceptance,
            document=None,
            readiness=ReadinessStatus.READY_FOR_PRODUCTION,
            acceptance_state=None,  # None because doc doesn't exist
            missing_inputs=[],
        )
        
        assert "will need acceptance" in subtitle.lower()

    def test_ready_no_acceptance_no_subtitle(
        self, status_service, mock_doc_type_no_acceptance
    ):
        """Ready document without acceptance requirement → no subtitle."""
        subtitle = status_service._derive_subtitle(
            doc_type=mock_doc_type_no_acceptance,
            document=MagicMock(),
            readiness=ReadinessStatus.PRODUCED,
            acceptance_state=None,
            missing_inputs=[],
        )
        
        assert subtitle is None


# =============================================================================
# CAN USE AS INPUT TESTS
# =============================================================================

class TestCanUseAsInput:
    """Test downstream gating logic."""

    def test_cannot_use_nonexistent_document(
        self, status_service, mock_doc_type_no_acceptance
    ):
        """Document must exist to be used as input."""
        can_use = status_service._derive_can_use_as_input(
            doc_type=mock_doc_type_no_acceptance,
            document=None,
            readiness=ReadinessStatus.READY_FOR_PRODUCTION,
            acceptance_state=None,
        )
        
        assert can_use is False

    def test_cannot_use_blocked_document(
        self, status_service, mock_doc_type_with_acceptance
    ):
        """Blocked documents cannot be used as input."""
        document = make_document("architecture_spec")
        
        can_use = status_service._derive_can_use_as_input(
            doc_type=mock_doc_type_with_acceptance,
            document=document,
            readiness=ReadinessStatus.REQUIREMENTS_NOT_MET,
            acceptance_state=AcceptanceState.NEEDS_ACCEPTANCE,
        )
        
        assert can_use is False

    def test_can_use_ready_no_acceptance(
        self, status_service, mock_doc_type_no_acceptance
    ):
        """Ready document without acceptance requirement → can use."""
        document = make_document("project_discovery")
        
        can_use = status_service._derive_can_use_as_input(
            doc_type=mock_doc_type_no_acceptance,
            document=document,
            readiness=ReadinessStatus.PRODUCED,
            acceptance_state=None,
        )
        
        assert can_use is True

    def test_cannot_use_without_acceptance(
        self, status_service, mock_doc_type_with_acceptance
    ):
        """Document requiring acceptance but not accepted → cannot use."""
        document = make_document("architecture_spec")
        
        can_use = status_service._derive_can_use_as_input(
            doc_type=mock_doc_type_with_acceptance,
            document=document,
            readiness=ReadinessStatus.PRODUCED,
            acceptance_state=AcceptanceState.NEEDS_ACCEPTANCE,
        )
        
        assert can_use is False

    def test_can_use_when_accepted(
        self, status_service, mock_doc_type_with_acceptance
    ):
        """Accepted document → can use."""
        document = make_document(
            "architecture_spec",
            accepted_at=datetime.now(timezone.utc),
        )
        
        can_use = status_service._derive_can_use_as_input(
            doc_type=mock_doc_type_with_acceptance,
            document=document,
            readiness=ReadinessStatus.PRODUCED,
            acceptance_state=AcceptanceState.ACCEPTED,
        )
        
        assert can_use is True

    def test_can_use_stale_accepted(
        self, status_service, mock_doc_type_with_acceptance
    ):
        """Stale + accepted → can use (with warning via subtitle)."""
        document = make_document(
            "architecture_spec",
            is_stale=True,
            accepted_at=datetime.now(timezone.utc),
        )
        
        can_use = status_service._derive_can_use_as_input(
            doc_type=mock_doc_type_with_acceptance,
            document=document,
            readiness=ReadinessStatus.STALE,
            acceptance_state=AcceptanceState.ACCEPTED,
        )
        
        assert can_use is True


# =============================================================================
# ACTION ENABLEMENT TESTS
# =============================================================================

class TestActionEnablement:
    """Test button enable/disable logic per ADR-007 Section 5."""

    def test_can_build_when_waiting(self, status_service, mock_doc_type_no_acceptance):
        """Can build when document doesn't exist (waiting)."""
        status = status_service._build_document_status(
            doc_type=mock_doc_type_no_acceptance,
            document=None,
            existing_type_ids=set(),
        )
        
        assert status.can_build is True
        assert status.can_rebuild is False

    def test_can_rebuild_when_stale(self, status_service, mock_doc_type_no_acceptance):
        """Can rebuild when document is stale."""
        document = make_document("project_discovery", is_stale=True)
        
        status = status_service._build_document_status(
            doc_type=mock_doc_type_no_acceptance,
            document=document,
            existing_type_ids={"project_discovery"},
        )
        
        assert status.can_build is True  # Can also build (overwrite)
        assert status.can_rebuild is True

    def test_cannot_build_when_blocked(
        self, status_service, mock_doc_type_with_acceptance
    ):
        """Cannot build when blocked by missing dependencies."""
        status = status_service._build_document_status(
            doc_type=mock_doc_type_with_acceptance,
            document=None,
            existing_type_ids=set(),  # Missing project_discovery
        )
        
        assert status.can_build is False
        assert status.can_rebuild is False

    def test_cannot_build_when_ready(self, status_service, mock_doc_type_no_acceptance):
        """Cannot build when document already exists and is current."""
        document = make_document("project_discovery", is_stale=False)
        
        status = status_service._build_document_status(
            doc_type=mock_doc_type_no_acceptance,
            document=document,
            existing_type_ids={"project_discovery"},
        )
        
        assert status.can_build is False
        assert status.can_rebuild is False

    def test_can_accept_when_needs_acceptance(
        self, status_service, mock_doc_type_with_acceptance
    ):
        """Can accept when document needs acceptance."""
        document = make_document("architecture_spec")
        
        status = status_service._build_document_status(
            doc_type=mock_doc_type_with_acceptance,
            document=document,
            existing_type_ids={"project_discovery", "architecture_spec"},
        )
        
        assert status.can_accept is True
        assert status.can_reject is True

    def test_cannot_accept_when_already_accepted(
        self, status_service, mock_doc_type_with_acceptance
    ):
        """Cannot accept when already accepted."""
        document = make_document(
            "architecture_spec",
            accepted_at=datetime.now(timezone.utc),
        )
        
        status = status_service._build_document_status(
            doc_type=mock_doc_type_with_acceptance,
            document=document,
            existing_type_ids={"project_discovery", "architecture_spec"},
        )
        
        assert status.can_accept is False
        # Can still request changes on accepted document
        assert status.can_reject is True


# =============================================================================
# FULL STATUS COMBINATION MATRIX
# =============================================================================

class TestStatusCombinationMatrix:
    """
    Test the full matrix of status combinations from ADR-007.
    
    This ensures all combinations behave correctly for UI interpretation.
    """

    def test_ready_no_acceptance(self, status_service, mock_doc_type_no_acceptance):
        """✅ (no acceptance) - Document is fine, doesn't need sign-off."""
        document = make_document("project_discovery", is_stale=False)
        
        status = status_service._build_document_status(
            doc_type=mock_doc_type_no_acceptance,
            document=document,
            existing_type_ids={"project_discovery"},
        )
        
        assert status.readiness == ReadinessStatus.PRODUCED
        assert status.acceptance_state is None
        assert status.subtitle is None
        assert status.can_use_as_input is True

    def test_ready_accepted(self, status_service, mock_doc_type_with_acceptance):
        """✅ + 🟢 - Built, current, and approved — fully trusted."""
        document = make_document(
            "architecture_spec",
            is_stale=False,
            accepted_at=datetime.now(timezone.utc),
        )
        
        status = status_service._build_document_status(
            doc_type=mock_doc_type_with_acceptance,
            document=document,
            existing_type_ids={"project_discovery", "architecture_spec"},
        )
        
        assert status.readiness == ReadinessStatus.PRODUCED
        assert status.acceptance_state == AcceptanceState.ACCEPTED
        assert status.can_use_as_input is True

    def test_stale_accepted(self, status_service, mock_doc_type_with_acceptance):
        """⚠️ + 🟢 - Approved, but inputs changed — review recommended."""
        document = make_document(
            "architecture_spec",
            is_stale=True,
            accepted_at=datetime.now(timezone.utc),
        )
        
        status = status_service._build_document_status(
            doc_type=mock_doc_type_with_acceptance,
            document=document,
            existing_type_ids={"project_discovery", "architecture_spec"},
        )
        
        assert status.readiness == ReadinessStatus.STALE
        assert status.acceptance_state == AcceptanceState.ACCEPTED
        assert "review recommended" in status.subtitle.lower()
        assert status.can_use_as_input is True  # Still allowed with warning

    def test_stale_needs_acceptance(self, status_service, mock_doc_type_with_acceptance):
        """⚠️ + 🟡 - Stale and needs approval — review before trusting."""
        document = make_document("architecture_spec", is_stale=True)
        
        status = status_service._build_document_status(
            doc_type=mock_doc_type_with_acceptance,
            document=document,
            existing_type_ids={"project_discovery", "architecture_spec"},
        )
        
        assert status.readiness == ReadinessStatus.STALE
        assert status.acceptance_state == AcceptanceState.NEEDS_ACCEPTANCE
        assert status.can_use_as_input is False

    def test_blocked_no_acceptance(self, status_service, mock_doc_type_with_acceptance):
        """❌ (no acceptance) - Can't build yet — prerequisites missing."""
        status = status_service._build_document_status(
            doc_type=mock_doc_type_with_acceptance,
            document=None,
            existing_type_ids=set(),  # Missing project_discovery
        )
        
        assert status.readiness == ReadinessStatus.REQUIREMENTS_NOT_MET
        assert status.acceptance_state is None  # Can't accept non-existent doc
        assert "Missing:" in status.subtitle
        assert status.can_build is False
        assert status.can_use_as_input is False

    def test_waiting_no_acceptance(self, status_service, mock_doc_type_no_acceptance):
        """⏳ (no acceptance) - Ready to build — prerequisites met."""
        status = status_service._build_document_status(
            doc_type=mock_doc_type_no_acceptance,
            document=None,
            existing_type_ids=set(),
        )
        
        assert status.readiness == ReadinessStatus.READY_FOR_PRODUCTION
        assert status.acceptance_state is None
        assert status.can_build is True

    def test_waiting_acceptance_required(
        self, status_service, mock_doc_type_with_acceptance
    ):
        """⏳ (acceptance required) - Ready to build — will need acceptance."""
        status = status_service._build_document_status(
            doc_type=mock_doc_type_with_acceptance,
            document=None,
            existing_type_ids={"project_discovery"},  # Deps met
        )
        
        assert status.readiness == ReadinessStatus.READY_FOR_PRODUCTION
        assert status.acceptance_state is None  # Can't accept what doesn't exist
        assert "will need acceptance" in status.subtitle.lower()
        assert status.can_build is True


# =============================================================================
# INTEGRATION-STYLE TESTS (with mocked DB)
# =============================================================================

class TestServiceIntegration:
    """Test service methods with mocked database calls."""

    @pytest.mark.asyncio
    async def test_get_project_document_statuses(self, status_service):
        """Test full workflow of getting all document statuses for a project."""
        project_id = uuid4()
        
        # Mock the database query methods
        mock_doc_types = [
            MagicMock(
                doc_type_id="project_discovery",
                name="Product Discovery",
                icon="search",
                acceptance_required=False,
                accepted_by_role=None,
                required_inputs=[],
                display_order=1,
            ),
            MagicMock(
                doc_type_id="architecture_spec",
                name="Technical Architecture",
                icon="landmark",
                acceptance_required=True,
                accepted_by_role="architect",
                required_inputs=["project_discovery"],
                display_order=2,
            ),
        ]
        
        mock_documents = [
            make_document("project_discovery", is_stale=False),
        ]
        
        with patch.object(
            status_service, "_get_project_document_types", new_callable=AsyncMock
        ) as mock_get_types, patch.object(
            status_service, "_get_project_documents", new_callable=AsyncMock
        ) as mock_get_docs:
            mock_get_types.return_value = mock_doc_types
            mock_get_docs.return_value = mock_documents
            
            mock_db = AsyncMock()
            statuses = await status_service.get_project_document_statuses(
                mock_db, project_id
            )
        
        assert len(statuses) == 2
        
        # First doc type - exists, ready
        assert statuses[0].doc_type_id == "project_discovery"
        assert statuses[0].readiness == ReadinessStatus.PRODUCED
        assert statuses[0].can_use_as_input is True
        
        # Second doc type - doesn't exist, waiting (deps met)
        assert statuses[1].doc_type_id == "architecture_spec"
        assert statuses[1].readiness == ReadinessStatus.READY_FOR_PRODUCTION
        assert statuses[1].can_build is True

    @pytest.mark.asyncio
    async def test_statuses_sorted_by_display_order(self, status_service):
        """Test that returned statuses are sorted by display_order."""
        project_id = uuid4()
        
        # Create doc types in wrong order
        mock_doc_types = [
            MagicMock(
                doc_type_id="third",
                name="Third",
                icon="3",
                acceptance_required=False,
                accepted_by_role=None,
                required_inputs=[],
                display_order=30,
            ),
            MagicMock(
                doc_type_id="first",
                name="First",
                icon="1",
                acceptance_required=False,
                accepted_by_role=None,
                required_inputs=[],
                display_order=10,
            ),
            MagicMock(
                doc_type_id="second",
                name="Second",
                icon="2",
                acceptance_required=False,
                accepted_by_role=None,
                required_inputs=[],
                display_order=20,
            ),
        ]
        
        with patch.object(
            status_service, "_get_project_document_types", new_callable=AsyncMock
        ) as mock_get_types, patch.object(
            status_service, "_get_project_documents", new_callable=AsyncMock
        ) as mock_get_docs:
            mock_get_types.return_value = mock_doc_types
            mock_get_docs.return_value = []
            
            mock_db = AsyncMock()
            statuses = await status_service.get_project_document_statuses(
                mock_db, project_id
            )
        
        # Verify sorted by display_order
        assert [s.doc_type_id for s in statuses] == ["first", "second", "third"]


# =============================================================================
# DOCUMENT STATUS DATACLASS TESTS
# =============================================================================

class TestDocumentStatusDataclass:
    """Test DocumentStatus dataclass methods."""

    def test_to_dict(self, status_service, mock_doc_type_no_acceptance):
        """Test to_dict serialization."""
        document = make_document("project_discovery")
        
        status = status_service._build_document_status(
            doc_type=mock_doc_type_no_acceptance,
            document=document,
            existing_type_ids={"project_discovery"},
        )
        
        result = status.to_dict()
        
        assert result["doc_type_id"] == "project_discovery"
        assert result["title"] == "Product Discovery"
        assert result["icon"] == "search"
        assert result["readiness"] == "produced"
        assert result["acceptance_state"] is None
        assert result["can_build"] is False
        assert result["can_use_as_input"] is True
        assert isinstance(result["document_id"], str)  # UUID serialized


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_required_inputs(self, status_service):
        """Document type with None required_inputs doesn't crash."""
        doc_type = MagicMock()
        doc_type.doc_type_id = "test"
        doc_type.name = "Test"
        doc_type.icon = "test"
        doc_type.acceptance_required = False
        doc_type.accepted_by_role = None
        doc_type.required_inputs = None  # None instead of []
        doc_type.display_order = 1
        
        # Should not raise
        status = status_service._build_document_status(
            doc_type=doc_type,
            document=None,
            existing_type_ids=set(),
        )
        
        assert status.readiness == ReadinessStatus.READY_FOR_PRODUCTION

    def test_none_display_order(self, status_service):
        """Document type with None display_order defaults to 0."""
        doc_type = MagicMock()
        doc_type.doc_type_id = "test"
        doc_type.name = "Test"
        doc_type.icon = "test"
        doc_type.acceptance_required = False
        doc_type.accepted_by_role = None
        doc_type.required_inputs = []
        doc_type.display_order = None
        
        status = status_service._build_document_status(
            doc_type=doc_type,
            document=None,
            existing_type_ids=set(),
        )
        
        assert status.display_order == 0

    def test_none_accepted_by_role_fallback(self, status_service):
        """Missing accepted_by_role falls back to 'reviewer'."""
        doc_type = MagicMock()
        doc_type.doc_type_id = "test"
        doc_type.name = "Test"
        doc_type.icon = "test"
        doc_type.acceptance_required = True
        doc_type.accepted_by_role = None  # No role specified
        doc_type.required_inputs = []
        doc_type.display_order = 1
        
        status = status_service._build_document_status(
            doc_type=doc_type,
            document=None,
            existing_type_ids=set(),
        )
        
        assert "Reviewer" in status.subtitle  # Fallback role


if __name__ == "__main__":
    pytest.main([__file__, "-v"])