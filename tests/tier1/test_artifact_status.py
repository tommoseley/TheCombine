"""Tests for ArtifactStatus model and transitions (WS-REWIND-002)."""

import pytest

from app.domain.models.artifact_status import (
    ArtifactStatus,
    IllegalTransitionError,
    LEGAL_TRANSITIONS,
    validate_transition,
)


class TestArtifactStatusEnum:
    """Three statuses, no more."""

    def test_exactly_three_statuses(self):
        assert len(list(ArtifactStatus)) == 3

    def test_current_value(self):
        assert ArtifactStatus.CURRENT.value == "current"

    def test_stale_value(self):
        assert ArtifactStatus.STALE.value == "stale"

    def test_superseded_value(self):
        assert ArtifactStatus.SUPERSEDED.value == "superseded"


class TestLegalTransitions:
    """Transition rules are deterministic."""

    def test_current_to_stale_allowed(self):
        assert validate_transition(ArtifactStatus.CURRENT, ArtifactStatus.STALE)

    def test_current_to_superseded_allowed(self):
        assert validate_transition(ArtifactStatus.CURRENT, ArtifactStatus.SUPERSEDED)

    def test_stale_to_superseded_allowed(self):
        assert validate_transition(ArtifactStatus.STALE, ArtifactStatus.SUPERSEDED)


class TestIllegalTransitions:
    """Illegal transitions are rejected."""

    def test_stale_to_current_rejected(self):
        assert not validate_transition(ArtifactStatus.STALE, ArtifactStatus.CURRENT)

    def test_superseded_to_current_rejected(self):
        assert not validate_transition(ArtifactStatus.SUPERSEDED, ArtifactStatus.CURRENT)

    def test_superseded_to_stale_rejected(self):
        assert not validate_transition(ArtifactStatus.SUPERSEDED, ArtifactStatus.STALE)

    def test_current_to_current_rejected(self):
        assert not validate_transition(ArtifactStatus.CURRENT, ArtifactStatus.CURRENT)

    def test_stale_to_stale_rejected(self):
        assert not validate_transition(ArtifactStatus.STALE, ArtifactStatus.STALE)

    def test_superseded_to_superseded_rejected(self):
        assert not validate_transition(ArtifactStatus.SUPERSEDED, ArtifactStatus.SUPERSEDED)


class TestSupersededIsTerminal:
    """Superseded is a terminal state — no transitions out."""

    def test_no_transitions_from_superseded(self):
        allowed = LEGAL_TRANSITIONS[ArtifactStatus.SUPERSEDED]
        assert len(allowed) == 0


class TestIllegalTransitionError:
    """Error includes actionable details."""

    def test_error_message_includes_from_and_to(self):
        err = IllegalTransitionError(ArtifactStatus.STALE, ArtifactStatus.CURRENT)
        assert "stale" in str(err)
        assert "current" in str(err)

    def test_error_message_includes_allowed(self):
        err = IllegalTransitionError(ArtifactStatus.STALE, ArtifactStatus.CURRENT)
        assert "superseded" in str(err)

    def test_error_attributes(self):
        err = IllegalTransitionError(ArtifactStatus.CURRENT, ArtifactStatus.CURRENT)
        assert err.from_status == ArtifactStatus.CURRENT
        assert err.to_status == ArtifactStatus.CURRENT


class TestTransitionCompleteness:
    """Every status has a defined transition set (even if empty)."""

    def test_all_statuses_have_transition_entry(self):
        for status in ArtifactStatus:
            assert status in LEGAL_TRANSITIONS
