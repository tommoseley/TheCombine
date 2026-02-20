"""Tests for operational error UI affordances (WS-OPS-001 Criteria 8-9, Mode B).

Mode B = source inspection. We verify the UI source files contain the
required operational error handling, retry button, and API field.

C8: Error message shown — ConciergeIntakeSidecar.jsx contains operational error check
    and "temporarily unavailable" text.
C9: Retry works — sidecar has "Retry" button; useConciergeIntake.js exposes retry
    capability; intake.py includes operational_error field.
"""

import os

import pytest


SPA_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "spa", "src")
APP_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "app")


def _read_source(relative_path: str) -> str:
    """Read a source file relative to project root."""
    project_root = os.path.join(os.path.dirname(__file__), "..", "..")
    full_path = os.path.normpath(os.path.join(project_root, relative_path))
    with open(full_path) as f:
        return f.read()


class TestErrorMessageShown:
    """C8: ConciergeIntakeSidecar.jsx shows operational error state."""

    def test_sidecar_checks_operational_error(self):
        source = _read_source("spa/src/components/ConciergeIntakeSidecar.jsx")
        assert "operationalError" in source, (
            "ConciergeIntakeSidecar.jsx must check for operationalError state"
        )

    def test_sidecar_shows_temporarily_unavailable(self):
        source = _read_source("spa/src/components/ConciergeIntakeSidecar.jsx")
        assert "temporarily unavailable" in source.lower(), (
            "ConciergeIntakeSidecar.jsx must show 'temporarily unavailable' message"
        )


class TestRetryWorks:
    """C9: Retry affordance exists across UI, hook, and API layers."""

    def test_sidecar_has_retry_button(self):
        source = _read_source("spa/src/components/ConciergeIntakeSidecar.jsx")
        # Must have a retry button (case-insensitive check for "retry" in button text or handler)
        assert "retry" in source.lower(), (
            "ConciergeIntakeSidecar.jsx must have a Retry button"
        )
        assert "retryLastMessage" in source, (
            "ConciergeIntakeSidecar.jsx must call retryLastMessage"
        )

    def test_hook_exposes_retry_capability(self):
        source = _read_source("spa/src/hooks/useConciergeIntake.js")
        assert "retryLastMessage" in source, (
            "useConciergeIntake.js must expose retryLastMessage"
        )
        assert "operationalError" in source, (
            "useConciergeIntake.js must expose operationalError state"
        )

    def test_api_includes_operational_error_field(self):
        source = _read_source("app/api/v1/routers/intake.py")
        assert "operational_error" in source, (
            "intake.py must include operational_error field in response model"
        )
