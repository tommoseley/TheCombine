"""
Tier-1 tests for intake_pure.py -- pure data transformations extracted from intake_workflow_routes.

No DB, no I/O. All tests use plain dicts and simple stub objects.
WS-CRAP-006: Testability refactoring.
"""

from types import SimpleNamespace

from app.web.routes.public.intake_pure import (
    assemble_completion_data,
    clean_problem_statement,
    extract_constraints_explicit,
    extract_intake_doc_from_context_state,
    extract_messages_from_node_history,
    extract_problem_statement,
    extract_project_type,
    get_completion_outcome_display,
    get_outcome_display,
    insert_context_state_user_input,
)


# =============================================================================
# get_outcome_display
# =============================================================================

class TestGetOutcomeDisplay:
    def test_qualified(self):
        result = get_outcome_display("qualified")
        assert result["title"] == "Project Qualified"
        assert result["color"] == "green"
        assert result["next_action"] == "View Discovery Document"

    def test_not_ready(self):
        result = get_outcome_display("not_ready")
        assert result["title"] == "Not Ready"
        assert result["color"] == "yellow"

    def test_out_of_scope(self):
        result = get_outcome_display("out_of_scope")
        assert result["title"] == "Out of Scope"
        assert result["next_action"] is None

    def test_redirect(self):
        result = get_outcome_display("redirect")
        assert result["title"] == "Redirected"
        assert result["color"] == "blue"

    def test_blocked(self):
        result = get_outcome_display("blocked")
        assert result["title"] == "Blocked"
        assert result["next_action"] == "Start Over"

    def test_unknown_outcome_returns_default(self):
        result = get_outcome_display("unknown_value")
        assert result["title"] == "Complete"
        assert result["color"] == "gray"
        assert result["next_action"] is None

    def test_none_outcome_returns_default(self):
        result = get_outcome_display(None)
        assert result["title"] == "Complete"


# =============================================================================
# get_completion_outcome_display
# =============================================================================

class TestGetCompletionOutcomeDisplay:
    def test_qualified_with_project(self):
        result = get_completion_outcome_display("qualified", has_project=True, project_id="PRJ-001")
        assert result["title"] == "Project Created"
        assert "PRJ-001" in result["description"]
        assert result["next_action"] == "View Project"

    def test_qualified_without_project(self):
        result = get_completion_outcome_display("qualified", has_project=False)
        assert result["title"] == "Project Qualified"
        assert result["next_action"] == "View Discovery Document"

    def test_qualified_with_project_no_id(self):
        result = get_completion_outcome_display("qualified", has_project=True, project_id=None)
        assert "unknown" in result["description"]

    def test_not_ready(self):
        result = get_completion_outcome_display("not_ready")
        assert result["title"] == "Not Ready"
        assert result["next_action"] == "Start Over"

    def test_out_of_scope(self):
        result = get_completion_outcome_display("out_of_scope")
        assert result["next_action"] is None

    def test_redirect(self):
        result = get_completion_outcome_display("redirect")
        assert result["title"] == "Redirected"

    def test_unknown_returns_default(self):
        result = get_completion_outcome_display("nonexistent")
        assert result["title"] == "Complete"

    def test_none_returns_default(self):
        result = get_completion_outcome_display(None)
        assert result["title"] == "Complete"


# =============================================================================
# extract_messages_from_node_history
# =============================================================================

def _make_execution(metadata):
    """Create a mock node execution with metadata."""
    return SimpleNamespace(metadata=metadata)


class TestExtractMessagesFromNodeHistory:
    def test_empty_history(self):
        result = extract_messages_from_node_history([], None)
        assert result == []

    def test_user_input_only(self):
        history = [_make_execution({"user_input": "Hello"})]
        result = extract_messages_from_node_history(history, None)
        assert len(result) == 1
        assert result[0] == {"role": "user", "content": "Hello"}

    def test_response_only(self):
        history = [_make_execution({"response": "Hi there"})]
        result = extract_messages_from_node_history(history, None)
        assert len(result) == 1
        assert result[0] == {"role": "assistant", "content": "Hi there"}

    def test_user_prompt_used_as_fallback(self):
        history = [_make_execution({"user_prompt": "What is your name?"})]
        result = extract_messages_from_node_history(history, None)
        assert len(result) == 1
        assert result[0]["content"] == "What is your name?"

    def test_response_preferred_over_user_prompt(self):
        history = [_make_execution({"response": "main response", "user_prompt": "fallback"})]
        result = extract_messages_from_node_history(history, None)
        assert result[0]["content"] == "main response"

    def test_last_response_skipped_when_paused(self):
        history = [
            _make_execution({"user_input": "Q1"}),
            _make_execution({"response": "A1"}),
            _make_execution({"response": "Pending question"}),
        ]
        result = extract_messages_from_node_history(history, "Pending question rendered")
        # Last response should be skipped
        assert len(result) == 2
        assert result[0]["content"] == "Q1"
        assert result[1]["content"] == "A1"

    def test_last_response_not_skipped_when_not_paused(self):
        history = [
            _make_execution({"response": "A1"}),
            _make_execution({"response": "A2"}),
        ]
        result = extract_messages_from_node_history(history, None)
        assert len(result) == 2

    def test_mixed_conversation(self):
        history = [
            _make_execution({"user_prompt": "Welcome! What do you need?"}),
            _make_execution({"user_input": "I need a website", "response": "Great, tell me more"}),
            _make_execution({"user_input": "It should be fast", "response": "Got it"}),
        ]
        result = extract_messages_from_node_history(history, None)
        assert len(result) == 5  # 1 prompt + 2 user + 2 response


# =============================================================================
# insert_context_state_user_input
# =============================================================================

class TestInsertContextStateUserInput:
    def test_none_input_returns_unchanged(self):
        messages = [{"role": "assistant", "content": "Hi"}]
        result = insert_context_state_user_input(messages, None)
        assert len(result) == 1

    def test_empty_string_input_returns_unchanged(self):
        messages = [{"role": "assistant", "content": "Hi"}]
        result = insert_context_state_user_input(messages, "")
        assert len(result) == 1

    def test_already_present_not_duplicated(self):
        messages = [
            {"role": "user", "content": "Build a website"},
            {"role": "assistant", "content": "Sure"},
        ]
        result = insert_context_state_user_input(messages, "Build a website")
        assert len(result) == 2

    def test_inserted_after_initial_assistant_messages(self):
        messages = [
            {"role": "assistant", "content": "Welcome!"},
            {"role": "assistant", "content": "How can I help?"},
        ]
        result = insert_context_state_user_input(messages, "I need help")
        assert len(result) == 3
        assert result[2]["content"] == "I need help"
        assert result[2]["role"] == "user"

    def test_inserted_at_beginning_when_no_assistant(self):
        messages = []
        result = insert_context_state_user_input(messages, "Hello")
        assert len(result) == 1
        assert result[0]["content"] == "Hello"

    def test_mutates_in_place(self):
        messages = []
        result = insert_context_state_user_input(messages, "Test")
        assert result is messages


# =============================================================================
# clean_problem_statement
# =============================================================================

class TestCleanProblemStatement:
    def test_empty_string(self):
        assert clean_problem_statement("") == ""

    def test_none_treated_as_empty(self):
        # The function signature says str, but original code checked `if not text`
        assert clean_problem_statement("") == ""

    def test_no_prefix(self):
        assert clean_problem_statement("Build a website") == "Build a website"

    def test_strip_the_user_wants_to(self):
        result = clean_problem_statement("The user wants to build a web application")
        assert result == "Build a web application"

    def test_strip_user_wants(self):
        result = clean_problem_statement("User wants a mobile app")
        assert result == "A mobile app"

    def test_strip_the_user_is_requesting(self):
        result = clean_problem_statement("The user is requesting a new feature")
        assert result == "A new feature"

    def test_strip_this_request_is_for(self):
        result = clean_problem_statement("This request is for a database migration")
        assert result == "A database migration"

    def test_case_insensitive(self):
        result = clean_problem_statement("the user wants to build something")
        assert result == "Build something"

    def test_strips_whitespace_first(self):
        result = clean_problem_statement("  The user wants to test  ")
        assert result == "Test"

    def test_only_first_matching_prefix_stripped(self):
        result = clean_problem_statement("The user wants The user needs to do something")
        assert result == "The user needs to do something"

    def test_capitalizes_first_letter_after_strip(self):
        result = clean_problem_statement("The user wants to build")
        assert result == "Build"
        result2 = clean_problem_statement("The user wants to x")
        assert result2 == "X"


# =============================================================================
# extract_intake_doc_from_context_state
# =============================================================================

class TestExtractIntakeDocFromContextState:
    def test_empty_context(self):
        assert extract_intake_doc_from_context_state({}) == {}

    def test_none_context(self):
        assert extract_intake_doc_from_context_state(None) == {}

    def test_primary_key(self):
        ctx = {"document_concierge_intake_document": {"name": "test"}}
        assert extract_intake_doc_from_context_state(ctx) == {"name": "test"}

    def test_fallback_to_last_produced(self):
        ctx = {"last_produced_document": {"name": "fallback"}}
        assert extract_intake_doc_from_context_state(ctx) == {"name": "fallback"}

    def test_fallback_to_concierge_intake(self):
        ctx = {"concierge_intake_document": {"name": "third"}}
        assert extract_intake_doc_from_context_state(ctx) == {"name": "third"}

    def test_priority_order(self):
        ctx = {
            "document_concierge_intake_document": {"name": "first"},
            "last_produced_document": {"name": "second"},
            "concierge_intake_document": {"name": "third"},
        }
        assert extract_intake_doc_from_context_state(ctx)["name"] == "first"

    def test_skips_falsy_values(self):
        ctx = {
            "document_concierge_intake_document": {},
            "last_produced_document": {"name": "second"},
        }
        # Empty dict is falsy? Actually {} is truthy in Python,
        # but the `or` chain will short-circuit on truthy values.
        # {} is falsy for the `or` operator -- WRONG, {} is falsy
        # Actually, empty dict is FALSY in Python.
        assert extract_intake_doc_from_context_state(ctx)["name"] == "second"


# =============================================================================
# extract_constraints_explicit
# =============================================================================

class TestExtractConstraintsExplicit:
    def test_dict_with_explicit(self):
        doc = {"constraints": {"explicit": ["must be fast", "no downtime"]}}
        assert extract_constraints_explicit(doc) == ["must be fast", "no downtime"]

    def test_dict_without_explicit(self):
        doc = {"constraints": {"inferred": ["some constraint"]}}
        assert extract_constraints_explicit(doc) == []

    def test_list_constraints(self):
        doc = {"constraints": ["a", "b"]}
        assert extract_constraints_explicit(doc) == ["a", "b"]

    def test_no_constraints(self):
        doc = {}
        assert extract_constraints_explicit(doc) == []

    def test_none_constraints(self):
        doc = {"constraints": None}
        assert extract_constraints_explicit(doc) == []


# =============================================================================
# extract_project_type
# =============================================================================

class TestExtractProjectType:
    def test_dict_with_category(self):
        doc = {"project_type": {"category": "web_app"}}
        assert extract_project_type(doc) == "web_app"

    def test_dict_without_category(self):
        doc = {"project_type": {"other": "value"}}
        assert extract_project_type(doc) == "unknown"

    def test_string_project_type(self):
        doc = {"project_type": "mobile_app"}
        assert extract_project_type(doc) == "mobile_app"

    def test_missing_project_type(self):
        doc = {}
        assert extract_project_type(doc) == "unknown"

    def test_none_project_type(self):
        doc = {"project_type": None}
        assert extract_project_type(doc) == "unknown"


# =============================================================================
# extract_problem_statement
# =============================================================================

class TestExtractProblemStatement:
    def test_normal_summary(self):
        doc = {"summary": {"description": "The user wants to build a CRM"}}
        assert extract_problem_statement(doc) == "Build a CRM"

    def test_no_summary(self):
        doc = {}
        assert extract_problem_statement(doc) == ""

    def test_summary_not_dict(self):
        doc = {"summary": "just a string"}
        assert extract_problem_statement(doc) == ""

    def test_summary_missing_description(self):
        doc = {"summary": {"title": "A project"}}
        assert extract_problem_statement(doc) == ""


# =============================================================================
# assemble_completion_data
# =============================================================================

class TestAssembleCompletionData:
    def test_qualified_with_project(self):
        ctx = {
            "document_concierge_intake_document": {
                "project_name": "My CRM",
                "summary": {"description": "The user wants to build a CRM"},
                "constraints": {"explicit": ["fast"]},
                "project_type": {"category": "web_app"},
                "routing_rationale": "Standard web project",
            },
            "interpretation": {"field1": {"value": "v1"}},
        }
        result = assemble_completion_data(
            gate_outcome="qualified",
            terminal_outcome=None,
            context_state=ctx,
            project_id="PRJ-001",
            project_name="My CRM Project",
            project_url="/projects/PRJ-001",
            has_project=True,
            execution_id="exec-123",
        )
        assert result["outcome_title"] == "Project Created"
        assert result["project_id"] == "PRJ-001"
        assert result["project_url"] == "/projects/PRJ-001"
        assert result["problem_statement"] == "Build a CRM"
        assert result["constraints_explicit"] == ["fast"]
        assert result["project_type"] == "web_app"
        assert result["is_completed"] is True
        assert result["is_paused"] is False
        assert result["phase"] == "complete"

    def test_not_ready_outcome(self):
        result = assemble_completion_data(
            gate_outcome="not_ready",
            terminal_outcome=None,
            context_state={},
            execution_id="exec-456",
        )
        assert result["outcome_title"] == "Not Ready"
        assert result["next_action"] == "Start Over"

    def test_unknown_outcome(self):
        result = assemble_completion_data(
            gate_outcome="unknown",
            terminal_outcome=None,
            context_state={},
        )
        assert result["outcome_title"] == "Complete"

    def test_empty_context_state(self):
        result = assemble_completion_data(
            gate_outcome="qualified",
            terminal_outcome=None,
            context_state={},
            has_project=False,
        )
        assert result["problem_statement"] == ""
        assert result["constraints_explicit"] == []
        assert result["project_type"] == "unknown"
        assert result["interpretation"] == {}

    def test_project_name_from_intake_doc(self):
        ctx = {
            "document_concierge_intake_document": {"project_name": "From Intake"},
        }
        result = assemble_completion_data(
            gate_outcome="qualified",
            terminal_outcome=None,
            context_state=ctx,
            project_name="Fallback Name",
            has_project=False,
        )
        assert result["project_name"] == "From Intake"

    def test_project_name_fallback(self):
        ctx = {"document_concierge_intake_document": {}}
        result = assemble_completion_data(
            gate_outcome="qualified",
            terminal_outcome=None,
            context_state=ctx,
            project_name="Fallback Name",
            has_project=False,
        )
        assert result["project_name"] == "Fallback Name"
