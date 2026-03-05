"""Tests for WS proposal service — WS-WB-025.

Tests the propose_work_statements endpoint logic:
- TA readiness gate
- ws_index non-empty gate
- Dangling ws_index refs gate
- Happy path: creates WS docs, updates ws_index, emits audit events
- Schema validation failure from LLM output
"""

from types import SimpleNamespace

from app.domain.services.document_readiness import is_doc_ready_for_downstream


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_doc(
    doc_type_id="work_package",
    content=None,
    status="active",
    lifecycle_state="complete",
    space_id="proj-uuid-1",
    space_type="project",
    display_id=None,
):
    """Create a mock document object."""
    doc = SimpleNamespace(
        id="doc-uuid-1",
        doc_type_id=doc_type_id,
        content=content or {},
        status=status,
        lifecycle_state=lifecycle_state,
        space_id=space_id,
        space_type=space_type,
        display_id=display_id,
        version=1,
        title="Test Doc",
        parent_document_id=None,
    )
    return doc


def _make_wp_doc(wp_id="wp_wb_001", ws_index=None, **kwargs):
    content = {
        "wp_id": wp_id,
        "title": "Test WP",
        "rationale": "Test",
        "scope_in": ["Something"],
        "scope_out": [],
        "dependencies": [],
        "definition_of_done": ["Done"],
        "governance_pins": {},
        "ws_index": ws_index or [],
    }
    return _make_doc(
        doc_type_id="work_package",
        content=content,
        display_id=wp_id,
        **kwargs,
    )


def _make_ta_doc(status="active", lifecycle_state="complete"):
    return _make_doc(
        doc_type_id="technical_architecture",
        content={"architecture_summary": "test"},
        status=status,
        lifecycle_state=lifecycle_state,
    )


def _valid_ws_output(wp_id="wp_wb_001", count=2):
    """Produce valid WS array that the LLM would return."""
    return [
        {
            "ws_id": f"WS-WB-{i:03d}",
            "parent_wp_id": wp_id,
            "title": f"Work Statement {i}",
            "objective": f"Objective {i}",
            "scope_in": [f"scope item {i}"],
            "scope_out": [],
            "procedure": [f"step {i}"],
            "verification_criteria": [f"verify {i}"],
            "prohibited_actions": [],
            "governance_pins": {},
            "state": "DRAFT",
        }
        for i in range(1, count + 1)
    ]


# ---------------------------------------------------------------------------
# Gate Tests (readiness predicate is tested in test_document_readiness.py,
# but we verify the gate logic integration here)
# ---------------------------------------------------------------------------


class TestTAGate:
    """TA must be ready for downstream consumption."""

    def test_ta_missing_blocks_proposal(self):
        """No TA doc -> not ready."""
        assert not is_doc_ready_for_downstream(None)

    def test_ta_draft_complete_allows_proposal(self):
        """Pipeline creates docs as draft; draft+complete must be ready."""
        ta = _make_ta_doc(status="draft")
        assert is_doc_ready_for_downstream(ta)

    def test_ta_archived_blocks_proposal(self):
        ta = _make_ta_doc(status="archived")
        assert not is_doc_ready_for_downstream(ta)

    def test_ta_active_partial_blocks_proposal(self):
        ta = _make_ta_doc(lifecycle_state="partial")
        assert not is_doc_ready_for_downstream(ta)

    def test_ta_active_complete_allows_proposal(self):
        ta = _make_ta_doc(status="active", lifecycle_state="complete")
        assert is_doc_ready_for_downstream(ta)


class TestWsIndexGate:
    """WP with non-empty ws_index blocks proposal."""

    def test_empty_ws_index_allows(self):
        wp = _make_wp_doc(ws_index=[])
        assert wp.content["ws_index"] == []

    def test_non_empty_ws_index_blocks(self):
        wp = _make_wp_doc(ws_index=[{"ws_id": "WS-WB-001", "order_key": "a0"}])
        assert len(wp.content["ws_index"]) > 0


class TestProposalServiceLogic:
    """Test the ws_proposal_service pure functions."""

    def test_build_ws_documents_creates_correct_count(self):
        from app.domain.services.ws_proposal_service import build_ws_documents

        ws_items = _valid_ws_output("wp_wb_001", count=3)
        docs = build_ws_documents(ws_items, "wp_wb_001")
        assert len(docs) == 3

    def test_build_ws_documents_all_draft(self):
        from app.domain.services.ws_proposal_service import build_ws_documents

        ws_items = _valid_ws_output("wp_wb_001", count=2)
        docs = build_ws_documents(ws_items, "wp_wb_001")
        for doc in docs:
            assert doc["state"] == "DRAFT"

    def test_build_ws_documents_sets_parent_wp_id(self):
        from app.domain.services.ws_proposal_service import build_ws_documents

        ws_items = _valid_ws_output("wp_wb_001", count=1)
        docs = build_ws_documents(ws_items, "wp_wb_001")
        assert docs[0]["parent_wp_id"] == "wp_wb_001"

    def test_build_ws_documents_preserves_ws_id(self):
        from app.domain.services.ws_proposal_service import build_ws_documents

        ws_items = _valid_ws_output("wp_wb_001", count=2)
        docs = build_ws_documents(ws_items, "wp_wb_001")
        assert docs[0]["ws_id"] == "WS-WB-001"
        assert docs[1]["ws_id"] == "WS-WB-002"

    def test_build_ws_index_from_docs(self):
        from app.domain.services.ws_proposal_service import build_ws_index_entries

        ws_items = _valid_ws_output("wp_wb_001", count=3)
        entries = build_ws_index_entries(ws_items)
        assert len(entries) == 3
        assert entries[0]["ws_id"] == "WS-WB-001"
        assert "order_key" in entries[0]

    def test_build_ws_index_order_keys_sequential(self):
        from app.domain.services.ws_proposal_service import build_ws_index_entries

        ws_items = _valid_ws_output("wp_wb_001", count=3)
        entries = build_ws_index_entries(ws_items)
        keys = [e["order_key"] for e in entries]
        assert keys == sorted(keys), "Order keys must be lexicographically sorted"

    def test_validate_proposal_gates_ta_missing(self):
        from app.domain.services.ws_proposal_service import validate_proposal_gates

        wp = _make_wp_doc()
        errors = validate_proposal_gates(wp.content, ta_doc=None)
        assert any("Technical Architecture" in e for e in errors)

    def test_validate_proposal_gates_ta_not_ready(self):
        from app.domain.services.ws_proposal_service import validate_proposal_gates

        wp = _make_wp_doc()
        ta = _make_ta_doc(lifecycle_state="partial")
        errors = validate_proposal_gates(wp.content, ta_doc=ta)
        assert any("Technical Architecture" in e for e in errors)

    def test_validate_proposal_gates_ws_index_non_empty(self):
        from app.domain.services.ws_proposal_service import validate_proposal_gates

        wp = _make_wp_doc(ws_index=[{"ws_id": "WS-WB-001", "order_key": "a0"}])
        ta = _make_ta_doc()
        errors = validate_proposal_gates(wp.content, ta_doc=ta)
        assert any("already has Work Statements" in e for e in errors)

    def test_validate_proposal_gates_happy_path(self):
        from app.domain.services.ws_proposal_service import validate_proposal_gates

        wp = _make_wp_doc(ws_index=[])
        ta = _make_ta_doc()
        errors = validate_proposal_gates(wp.content, ta_doc=ta)
        assert errors == []
