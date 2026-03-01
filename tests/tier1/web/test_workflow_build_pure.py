"""
Tier-1 tests for workflow_build_pure.py -- pure data transformations extracted from workflow_build_routes.

No DB, no I/O. All tests use plain dicts and simple values.
WS-CRAP-006: Testability refactoring.
"""

from app.web.routes.public.workflow_build_pure import (
    classify_workflow_state,
    estimate_progress,
    get_doc_type_display,
    get_status_message,
    parse_pgc_form_data,
)


# =============================================================================
# parse_pgc_form_data
# =============================================================================

class TestParsePgcFormData:
    def test_empty_form(self):
        assert parse_pgc_form_data([]) == {}

    def test_single_text_answer(self):
        items = [("answers[q1]", "hello")]
        result = parse_pgc_form_data(items)
        assert result == {"q1": "hello"}

    def test_boolean_true(self):
        items = [("answers[q1]", "true")]
        result = parse_pgc_form_data(items)
        assert result["q1"] is True

    def test_boolean_false(self):
        items = [("answers[q1]", "false")]
        result = parse_pgc_form_data(items)
        assert result["q1"] is False

    def test_multi_select(self):
        items = [
            ("answers[q1][]", "option_a"),
            ("answers[q1][]", "option_b"),
            ("answers[q1][]", "option_c"),
        ]
        result = parse_pgc_form_data(items)
        assert result["q1"] == ["option_a", "option_b", "option_c"]

    def test_mixed_types(self):
        items = [
            ("answers[q1]", "text value"),
            ("answers[q2]", "true"),
            ("answers[q3][]", "a"),
            ("answers[q3][]", "b"),
        ]
        result = parse_pgc_form_data(items)
        assert result["q1"] == "text value"
        assert result["q2"] is True
        assert result["q3"] == ["a", "b"]

    def test_non_answer_keys_ignored(self):
        items = [
            ("answers[q1]", "val"),
            ("csrf_token", "abc123"),
            ("other_field", "ignored"),
        ]
        result = parse_pgc_form_data(items)
        assert result == {"q1": "val"}

    def test_multi_overrides_single(self):
        """Multi-select values override single values with same question_id."""
        items = [
            ("answers[q1]", "single_value"),
            ("answers[q1][]", "multi_a"),
            ("answers[q1][]", "multi_b"),
        ]
        result = parse_pgc_form_data(items)
        # multi_values.update overwrites
        assert result["q1"] == ["multi_a", "multi_b"]

    def test_question_id_with_dashes(self):
        items = [("answers[q-budget-range]", "10k-50k")]
        result = parse_pgc_form_data(items)
        assert result["q-budget-range"] == "10k-50k"


# =============================================================================
# estimate_progress
# =============================================================================

class TestEstimateProgress:
    def test_pgc_node(self):
        assert estimate_progress("pgc") == 10

    def test_generation_node(self):
        assert estimate_progress("generation") == 50

    def test_qa_node(self):
        assert estimate_progress("qa") == 80

    def test_persist_node(self):
        assert estimate_progress("persist") == 95

    def test_end_node(self):
        assert estimate_progress("end") == 100

    def test_unknown_node(self):
        assert estimate_progress("unknown_node") == 30


# =============================================================================
# get_status_message
# =============================================================================

class TestGetStatusMessage:
    def test_pgc(self):
        assert get_status_message("pgc") == "Preparing questions..."

    def test_generation(self):
        assert get_status_message("generation") == "Generating document..."

    def test_qa(self):
        assert get_status_message("qa") == "Validating quality..."

    def test_persist(self):
        assert get_status_message("persist") == "Saving document..."

    def test_end(self):
        assert get_status_message("end") == "Completing..."

    def test_unknown(self):
        assert get_status_message("custom_node") == "Processing..."


# =============================================================================
# get_doc_type_display
# =============================================================================

class TestGetDocTypeDisplay:
    def test_known_type(self):
        result = get_doc_type_display("project_discovery")
        assert result["name"] == "Project Discovery"
        assert result["icon"] == "compass"

    def test_unknown_type(self):
        result = get_doc_type_display("custom_type")
        assert result["name"] == "custom_type"
        assert result["icon"] == "file-text"

    def test_returns_copy(self):
        result1 = get_doc_type_display("project_discovery")
        result2 = get_doc_type_display("project_discovery")
        result1["name"] = "MUTATED"
        assert result2["name"] == "Project Discovery"


# =============================================================================
# classify_workflow_state
# =============================================================================

class TestClassifyWorkflowState:
    def test_completed(self):
        result = classify_workflow_state(
            status_value="completed",
            pending_user_input_payload=None,
            terminal_outcome=None,
            current_node_id="end",
        )
        assert result["workflow_state"] == "complete"

    def test_failed_with_outcome(self):
        result = classify_workflow_state(
            status_value="failed",
            pending_user_input_payload=None,
            terminal_outcome="Validation failed",
            current_node_id=None,
        )
        assert result["workflow_state"] == "failed"
        assert result["error_message"] == "Validation failed"

    def test_failed_without_outcome(self):
        result = classify_workflow_state(
            status_value="failed",
            pending_user_input_payload=None,
            terminal_outcome=None,
            current_node_id=None,
        )
        assert result["error_message"] == "Unknown error"

    def test_paused_with_questions(self):
        payload = {"questions": [{"id": "q1", "text": "What budget?"}]}
        result = classify_workflow_state(
            status_value="paused",
            pending_user_input_payload=payload,
            terminal_outcome=None,
            current_node_id="pgc",
        )
        assert result["workflow_state"] == "paused_pgc"
        assert len(result["questions"]) == 1
        assert result["pending_user_input_payload"] is payload

    def test_paused_with_empty_questions(self):
        payload = {"questions": []}
        result = classify_workflow_state(
            status_value="paused",
            pending_user_input_payload=payload,
            terminal_outcome=None,
            current_node_id="pgc",
        )
        assert result["workflow_state"] == "stale_paused"

    def test_paused_without_payload(self):
        result = classify_workflow_state(
            status_value="paused",
            pending_user_input_payload=None,
            terminal_outcome=None,
            current_node_id="pgc",
        )
        assert result["workflow_state"] == "stale_paused"
        assert "expired" in result["error_message"].lower()

    def test_running_pending(self):
        result = classify_workflow_state(
            status_value="pending",
            pending_user_input_payload=None,
            terminal_outcome=None,
            current_node_id="generation",
        )
        assert result["workflow_state"] == "running"
        assert result["progress"] == 50
        assert result["status_message"] == "Generating document..."

    def test_running_with_none_node(self):
        result = classify_workflow_state(
            status_value="running",
            pending_user_input_payload=None,
            terminal_outcome=None,
            current_node_id=None,
        )
        assert result["workflow_state"] == "running"
        assert result["progress"] == 30  # default
        assert result["status_message"] == "Processing..."
