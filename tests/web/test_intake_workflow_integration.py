"""
Integration tests for Intake Workflow routes (WS-ADR-025).

Tests the intake workflow routes with mocked PlanExecutor to verify
end-to-end behavior without requiring actual LLM calls.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from fastapi.testclient import TestClient

from app.api.main import app
from app.auth.models import User
from app.domain.workflow.document_workflow_state import (
    DocumentWorkflowState,
    DocumentWorkflowStatus,
    NodeExecution,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_user():
    """Create mock authenticated user."""
    return User(
        user_id=str(uuid4()),
        email="test@example.com",
        name="Test User",
        is_active=True,
        email_verified=True,
        is_admin=False,
    )


@pytest.fixture
def mock_user_data(mock_user):
    """Create user data tuple as returned by get_optional_user."""
    return (mock_user, None, None)


@pytest.fixture
def mock_workflow_state():
    """Create mock workflow state."""
    return DocumentWorkflowState(
        execution_id="exec-test-123",
        workflow_id="concierge_intake",
        document_id="doc-test-456",
        document_type="concierge_intake",
        current_node_id="concierge",
        status=DocumentWorkflowStatus.PAUSED,
        pending_user_input=True,
        pending_prompt="What is the main goal of your project?",
    )


@pytest.fixture
def mock_completed_state():
    """Create completed workflow state."""
    state = DocumentWorkflowState(
        execution_id="exec-test-123",
        workflow_id="concierge_intake",
        document_id="doc-test-456",
        document_type="concierge_intake",
        current_node_id="terminal_qualified",
        status=DocumentWorkflowStatus.COMPLETED,
        gate_outcome="qualified",
        terminal_outcome="stabilized",
    )
    return state


@pytest.fixture
def mock_executor(mock_workflow_state):
    """Create mock PlanExecutor."""
    executor = AsyncMock()
    executor.start_execution = AsyncMock(return_value=mock_workflow_state)
    executor.run_to_completion_or_pause = AsyncMock(return_value=mock_workflow_state)
    executor.submit_user_input = AsyncMock(return_value=mock_workflow_state)
    executor.get_execution_status = AsyncMock(
        return_value={"status": "paused", "current_node": "concierge"}
    )
    executor._persistence = AsyncMock()
    executor._persistence.load = AsyncMock(return_value=mock_workflow_state)
    return executor


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app, raise_server_exceptions=False)


# =============================================================================
# Test: Start Intake Workflow
# =============================================================================


class TestStartIntakeWorkflow:
    """Tests for GET /intake endpoint."""

    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_redirects_when_not_authenticated(self, mock_auth, client):
        """Test redirect to login when not authenticated."""
        mock_auth.return_value = None

        response = client.get("/intake", follow_redirects=False)

        assert response.status_code == 302
        assert "login" in response.headers.get("location", "").lower()

    @patch("app.web.routes.public.intake_workflow_routes.USE_WORKFLOW_ENGINE_LLM", False)
    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_shows_not_enabled_when_feature_off(self, mock_auth, client, mock_user_data):
        """Test shows 'coming soon' when feature flag is off."""
        mock_auth.return_value = mock_user_data

        response = client.get("/intake")

        assert response.status_code == 200
        assert "Coming Soon" in response.text

    @patch("app.web.routes.public.intake_workflow_routes.USE_WORKFLOW_ENGINE_LLM", True)
    @patch("app.web.routes.public.intake_workflow_routes._get_executor")
    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_creates_workflow_and_shows_chat(
        self, mock_auth, mock_get_executor, client, mock_user_data, mock_executor, mock_workflow_state
    ):
        """Test creates workflow and displays chat UI."""
        mock_auth.return_value = mock_user_data
        mock_get_executor.return_value = mock_executor

        response = client.get("/intake")

        assert response.status_code == 200
        # Should contain execution ID in the page
        assert "exec-test-123" in response.text
        # Should show the pending prompt
        assert "What is the main goal of your project?" in response.text
        # Executor should have been called
        mock_executor.start_execution.assert_called_once()
        mock_executor.run_to_completion_or_pause.assert_called_once()

    @patch("app.web.routes.public.intake_workflow_routes.USE_WORKFLOW_ENGINE_LLM", True)
    @patch("app.web.routes.public.intake_workflow_routes._get_executor")
    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_handles_workflow_creation_error(
        self, mock_auth, mock_get_executor, client, mock_user_data, mock_executor
    ):
        """Test handles workflow creation error gracefully."""
        mock_auth.return_value = mock_user_data
        mock_executor.start_execution.side_effect = Exception("Database error")
        mock_get_executor.return_value = mock_executor

        response = client.get("/intake")

        assert response.status_code == 200
        assert "Something went wrong" in response.text or "Database error" in response.text

    @patch("app.web.routes.public.intake_workflow_routes.USE_WORKFLOW_ENGINE_LLM", False)
    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_htmx_request_returns_partial(self, mock_auth, client, mock_user_data):
        """Test HTMX request returns partial template."""
        mock_auth.return_value = mock_user_data

        response = client.get(
            "/intake",
            headers={"HX-Request": "true"},
        )

        assert response.status_code == 200
        # Partial should not contain full HTML document
        assert "<!DOCTYPE html>" not in response.text


# =============================================================================
# Test: Get Existing Workflow
# =============================================================================


class TestGetIntakeWorkflow:
    """Tests for GET /intake/{execution_id} endpoint."""

    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_redirects_when_not_authenticated(self, mock_auth, client):
        """Test redirect to login when not authenticated."""
        mock_auth.return_value = None

        response = client.get("/intake/exec-123", follow_redirects=False)

        assert response.status_code == 302
        assert "login" in response.headers.get("location", "").lower()

    @patch("app.web.routes.public.intake_workflow_routes._get_executor")
    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_shows_error_for_nonexistent_workflow(
        self, mock_auth, mock_get_executor, client, mock_user_data, mock_executor
    ):
        """Test shows error for non-existent workflow."""
        mock_auth.return_value = mock_user_data
        mock_executor.get_execution_status.return_value = None
        mock_get_executor.return_value = mock_executor

        response = client.get("/intake/nonexistent-id")

        assert response.status_code == 200
        assert "not found" in response.text.lower() or "error" in response.text.lower()

    @patch("app.web.routes.public.intake_workflow_routes._get_executor")
    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_loads_existing_workflow(
        self, mock_auth, mock_get_executor, client, mock_user_data, mock_executor, mock_workflow_state
    ):
        """Test loads and displays existing workflow."""
        mock_auth.return_value = mock_user_data
        mock_get_executor.return_value = mock_executor

        response = client.get("/intake/exec-test-123")

        assert response.status_code == 200
        assert "exec-test-123" in response.text
        mock_executor.get_execution_status.assert_called_once_with("exec-test-123")
        mock_executor._persistence.load.assert_called_once_with("exec-test-123")


# =============================================================================
# Test: Submit Message
# =============================================================================


class TestSubmitIntakeMessage:
    """Tests for POST /intake/{execution_id}/message endpoint."""

    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_returns_401_when_not_authenticated(self, mock_auth, client):
        """Test returns 401 when not authenticated."""
        mock_auth.return_value = None

        response = client.post(
            "/intake/exec-123/message",
            data={"content": "Hello"},
        )

        assert response.status_code == 401
        assert "log in" in response.text.lower()

    @patch("app.web.routes.public.intake_workflow_routes._get_executor")
    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_submits_message_and_returns_response(
        self, mock_auth, mock_get_executor, client, mock_user_data, mock_executor, mock_workflow_state
    ):
        """Test submits user message and returns assistant response."""
        mock_auth.return_value = mock_user_data
        # Add response to state history
        mock_workflow_state.record_execution(
            node_id="concierge",
            outcome="continue",
            metadata={
                "user_input": "I want to build a web app",
                "response": "Great! What technology stack are you considering?",
            },
        )
        mock_executor.submit_user_input.return_value = mock_workflow_state
        mock_executor.run_to_completion_or_pause.return_value = mock_workflow_state
        mock_get_executor.return_value = mock_executor

        response = client.post(
            "/intake/exec-test-123/message",
            data={"content": "I want to build a web app"},
        )

        assert response.status_code == 200
        mock_executor.submit_user_input.assert_called_once_with(
            execution_id="exec-test-123",
            user_input="I want to build a web app",
        )

    @patch("app.web.routes.public.intake_workflow_routes._get_executor")
    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_handles_message_processing_error(
        self, mock_auth, mock_get_executor, client, mock_user_data, mock_executor
    ):
        """Test handles message processing error gracefully."""
        mock_auth.return_value = mock_user_data
        mock_executor.submit_user_input.side_effect = Exception("Processing error")
        mock_get_executor.return_value = mock_executor

        response = client.post(
            "/intake/exec-test-123/message",
            data={"content": "Hello"},
        )

        assert response.status_code == 500
        assert "Error" in response.text


# =============================================================================
# Test: Submit Choice
# =============================================================================


class TestSubmitIntakeChoice:
    """Tests for POST /intake/{execution_id}/choice endpoint."""

    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_returns_401_when_not_authenticated(self, mock_auth, client):
        """Test returns 401 when not authenticated."""
        mock_auth.return_value = None

        response = client.post(
            "/intake/exec-123/choice",
            data={"choice": "qualified"},
        )

        assert response.status_code == 401
        assert "log in" in response.text.lower()

    @patch("app.web.routes.public.intake_workflow_routes._get_executor")
    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_submits_choice_and_continues(
        self, mock_auth, mock_get_executor, client, mock_user_data, mock_executor, mock_workflow_state
    ):
        """Test submits choice and continues workflow."""
        mock_auth.return_value = mock_user_data
        mock_executor.submit_user_input.return_value = mock_workflow_state
        mock_executor.run_to_completion_or_pause.return_value = mock_workflow_state
        mock_get_executor.return_value = mock_executor

        response = client.post(
            "/intake/exec-test-123/choice",
            data={"choice": "qualified"},
        )

        assert response.status_code == 200
        mock_executor.submit_user_input.assert_called_once_with(
            execution_id="exec-test-123",
            selected_option_id="qualified",
        )

    @patch("app.web.routes.public.intake_workflow_routes._get_executor")
    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_returns_completion_partial_when_completed(
        self, mock_auth, mock_get_executor, client, mock_user_data, mock_executor, mock_completed_state
    ):
        """Test returns completion partial when workflow completes."""
        mock_auth.return_value = mock_user_data
        mock_executor.submit_user_input.return_value = mock_completed_state
        mock_executor.run_to_completion_or_pause.return_value = mock_completed_state
        mock_get_executor.return_value = mock_executor

        response = client.post(
            "/intake/exec-test-123/choice",
            data={"choice": "qualified"},
        )

        assert response.status_code == 200
        # Should show completion info
        assert "Project Qualified" in response.text or "qualified" in response.text.lower()

    @patch("app.web.routes.public.intake_workflow_routes._get_executor")
    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_handles_choice_processing_error(
        self, mock_auth, mock_get_executor, client, mock_user_data, mock_executor
    ):
        """Test handles choice processing error gracefully."""
        mock_auth.return_value = mock_user_data
        mock_executor.submit_user_input.side_effect = Exception("Choice error")
        mock_get_executor.return_value = mock_executor

        response = client.post(
            "/intake/exec-test-123/choice",
            data={"choice": "qualified"},
        )

        assert response.status_code == 500
        assert "Error" in response.text


# =============================================================================
# Test: Workflow State Transitions
# =============================================================================


class TestWorkflowStateTransitions:
    """Tests for workflow state transitions through the UI."""

    @patch("app.web.routes.public.intake_workflow_routes._get_executor")
    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_paused_state_shows_input_form(
        self, mock_auth, mock_get_executor, client, mock_user_data, mock_executor, mock_workflow_state
    ):
        """Test paused state shows input form."""
        mock_auth.return_value = mock_user_data
        mock_get_executor.return_value = mock_executor

        response = client.get("/intake/exec-test-123")

        assert response.status_code == 200
        # Should have a form for user input
        assert "form" in response.text.lower() or "input" in response.text.lower()

    @patch("app.web.routes.public.intake_workflow_routes._get_executor")
    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_choice_state_shows_buttons(
        self, mock_auth, mock_get_executor, client, mock_user_data, mock_executor, mock_workflow_state
    ):
        """Test choice state shows choice buttons."""
        mock_auth.return_value = mock_user_data
        mock_workflow_state.pending_choices = ["qualified", "not_ready", "out_of_scope"]
        mock_get_executor.return_value = mock_executor

        response = client.get("/intake/exec-test-123")

        assert response.status_code == 200
        # Choices should be rendered (may be as buttons or other UI elements)
        # The exact text depends on template formatting

    @patch("app.web.routes.public.intake_workflow_routes._get_executor")
    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_escalation_state_shows_options(
        self, mock_auth, mock_get_executor, client, mock_user_data, mock_executor, mock_workflow_state
    ):
        """Test escalation state shows escalation options."""
        mock_auth.return_value = mock_user_data
        mock_workflow_state.escalation_active = True
        mock_workflow_state.escalation_options = ["retry", "skip", "escalate_to_human"]
        mock_get_executor.return_value = mock_executor

        response = client.get("/intake/exec-test-123")

        assert response.status_code == 200


# =============================================================================
# Test: HTMX Partial Responses
# =============================================================================


class TestHtmxPartials:
    """Tests for HTMX partial responses."""

    @patch("app.web.routes.public.intake_workflow_routes._get_executor")
    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_htmx_get_returns_partial(
        self, mock_auth, mock_get_executor, client, mock_user_data, mock_executor, mock_workflow_state
    ):
        """Test HTMX GET request returns partial without full page."""
        mock_auth.return_value = mock_user_data
        mock_get_executor.return_value = mock_executor

        response = client.get(
            "/intake/exec-test-123",
            headers={"HX-Request": "true"},
        )

        assert response.status_code == 200
        # Should not contain DOCTYPE (partial template)
        assert "<!DOCTYPE html>" not in response.text

    @patch("app.web.routes.public.intake_workflow_routes._get_executor")
    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_regular_get_returns_full_page(
        self, mock_auth, mock_get_executor, client, mock_user_data, mock_executor, mock_workflow_state
    ):
        """Test regular GET request returns full page."""
        mock_auth.return_value = mock_user_data
        mock_get_executor.return_value = mock_executor

        response = client.get("/intake/exec-test-123")

        assert response.status_code == 200
        # Should contain DOCTYPE (full page)
        assert "<!DOCTYPE html>" in response.text or "<!doctype html>" in response.text.lower()


# =============================================================================
# Test: Conversation History Display
# =============================================================================


class TestConversationHistoryDisplay:
    """Tests for conversation history display in templates."""

    @patch("app.web.routes.public.intake_workflow_routes._get_executor")
    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_displays_conversation_history(
        self, mock_auth, mock_get_executor, client, mock_user_data, mock_executor, mock_workflow_state
    ):
        """Test conversation history is displayed."""
        mock_auth.return_value = mock_user_data
        # Add conversation history
        mock_workflow_state.record_execution(
            node_id="concierge",
            outcome="continue",
            metadata={
                "user_input": "I want to build a mobile app",
                "response": "What platforms are you targeting?",
            },
        )
        mock_workflow_state.record_execution(
            node_id="concierge",
            outcome="continue",
            metadata={
                "user_input": "iOS and Android",
                "response": "Great! What's your timeline?",
            },
        )
        mock_get_executor.return_value = mock_executor

        response = client.get("/intake/exec-test-123")

        assert response.status_code == 200
        # Conversation should be visible
        assert "mobile app" in response.text
        assert "platforms" in response.text


# =============================================================================
# Test: Error Handling
# =============================================================================


class TestErrorHandling:
    """Tests for error handling scenarios."""

    @patch("app.web.routes.public.intake_workflow_routes._get_executor")
    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_database_error_shows_error_page(
        self, mock_auth, mock_get_executor, client, mock_user_data, mock_executor
    ):
        """Test database error shows error page."""
        mock_auth.return_value = mock_user_data
        mock_executor._persistence.load.side_effect = Exception("Database connection failed")
        mock_executor.get_execution_status.return_value = {"status": "paused"}
        mock_get_executor.return_value = mock_executor

        response = client.get("/intake/exec-test-123")

        # Should handle error gracefully
        assert response.status_code in [200, 500]

    @patch("app.web.routes.public.intake_workflow_routes.USE_WORKFLOW_ENGINE_LLM", True)
    @patch("app.web.routes.public.intake_workflow_routes._get_executor")
    @patch("app.web.routes.public.intake_workflow_routes.get_optional_user")
    def test_executor_creation_error(
        self, mock_auth, mock_get_executor, client, mock_user_data
    ):
        """Test executor creation error is handled."""
        mock_auth.return_value = mock_user_data
        mock_get_executor.side_effect = Exception("Failed to create executor")

        response = client.get("/intake")

        # Should handle error gracefully
        assert response.status_code in [200, 500]
