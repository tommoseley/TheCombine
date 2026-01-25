"""Tests for human interaction forms.

Note: These tests are skipped because they depend on the old WorkflowRegistry
and execution service infrastructure which has been replaced by PlanRegistry
and PlanExecutor. The tests need to be rewritten for the new ADR-039 workflow
system.
"""

import pytest
from fastapi.testclient import TestClient


# All tests in this file are skipped pending infrastructure updates
pytestmark = pytest.mark.skip(reason="Tests require old WorkflowRegistry infrastructure - needs update for ADR-039 PlanRegistry")


class TestAcceptanceForm:
    """Tests for acceptance form page."""

    def test_acceptance_form_renders_when_waiting(self, client: TestClient):
        """Acceptance form renders when execution is waiting."""
        pass

    def test_acceptance_form_shows_document_type(self, client: TestClient):
        """Acceptance form shows which document needs review."""
        pass

    def test_accept_button_exists(self, client: TestClient):
        """Acceptance form has approve button."""
        pass

    def test_reject_button_exists(self, client: TestClient):
        """Acceptance form has reject button."""
        pass

    def test_comment_field_exists(self, client: TestClient):
        """Acceptance form has optional comment field."""
        pass

    def test_acceptance_redirects_when_not_waiting(self, client: TestClient):
        """Acceptance form redirects if not in waiting state."""
        pass


class TestClarificationForm:
    """Tests for clarification form page."""

    def test_clarification_form_renders_when_waiting(self, client: TestClient):
        """Clarification form renders when execution is waiting."""
        pass

    def test_clarification_form_shows_step(self, client: TestClient):
        """Clarification form shows which step needs answers."""
        pass

    def test_clarification_submit_redirects(self, client: TestClient):
        """Submitting clarification redirects to execution page."""
        pass

    def test_wrong_state_redirects(self, client: TestClient):
        """Clarification form redirects if not in waiting state."""
        pass
