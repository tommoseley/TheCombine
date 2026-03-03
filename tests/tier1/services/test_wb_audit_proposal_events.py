"""
Tests for WB audit proposal event types — WS-WB-024.

Verifies that the four proposal-station audit event types
(ws_proposal_requested, ws_proposal_rejected, ws_proposed,
wp_ws_index_updated) are accepted by build_audit_event and
produce correctly-structured event dicts.
"""

from datetime import datetime, timezone

import pytest

from app.domain.services.wb_audit_service import (
    SUPPORTED_EVENT_TYPES,
    build_audit_event,
)


# ===========================================================================
# Proposal event types are in the supported set
# ===========================================================================


PROPOSAL_EVENT_TYPES = {
    "ws_proposal_requested",
    "ws_proposal_rejected",
    "ws_proposed",
    "wp_ws_index_updated",
}


class TestProposalEventTypesRegistered:
    """All proposal event types must be in SUPPORTED_EVENT_TYPES."""

    @pytest.mark.parametrize("event_type", sorted(PROPOSAL_EVENT_TYPES))
    def test_event_type_in_supported_set(self, event_type):
        assert event_type in SUPPORTED_EVENT_TYPES


# ===========================================================================
# ws_proposal_requested
# ===========================================================================


class TestWsProposalRequested:
    """ws_proposal_requested — emitted when a propose-ws request starts."""

    def test_produces_valid_event_dict(self):
        result = build_audit_event(
            event_type="ws_proposal_requested",
            entity_id="wp-abc-123",
            entity_type="work_package",
            mutation_data={
                "wp_id": "wp-abc-123",
                "project_id": "proj-001",
                "ta_version": "v2",
            },
        )
        assert result["event_type"] == "ws_proposal_requested"
        assert result["entity_id"] == "wp-abc-123"
        assert result["entity_type"] == "work_package"

    def test_mutation_data_contains_expected_payload(self):
        payload = {
            "wp_id": "wp-abc-123",
            "project_id": "proj-001",
            "ta_version": "v2",
        }
        result = build_audit_event(
            event_type="ws_proposal_requested",
            entity_id="wp-abc-123",
            entity_type="work_package",
            mutation_data=payload,
        )
        assert result["mutation_data"]["wp_id"] == "wp-abc-123"
        assert result["mutation_data"]["project_id"] == "proj-001"
        assert result["mutation_data"]["ta_version"] == "v2"

    def test_ta_version_optional_in_payload(self):
        """ta_version may be absent if not available."""
        payload = {"wp_id": "wp-abc-123", "project_id": "proj-001"}
        result = build_audit_event(
            event_type="ws_proposal_requested",
            entity_id="wp-abc-123",
            entity_type="work_package",
            mutation_data=payload,
        )
        assert "ta_version" not in result["mutation_data"]


# ===========================================================================
# ws_proposal_rejected
# ===========================================================================


class TestWsProposalRejected:
    """ws_proposal_rejected — emitted when a gate check fails."""

    def test_produces_valid_event_dict(self):
        result = build_audit_event(
            event_type="ws_proposal_rejected",
            entity_id="wp-abc-123",
            entity_type="work_package",
            mutation_data={
                "wp_id": "wp-abc-123",
                "project_id": "proj-001",
                "reason": "TA review not yet complete",
            },
        )
        assert result["event_type"] == "ws_proposal_rejected"
        assert result["entity_id"] == "wp-abc-123"
        assert result["entity_type"] == "work_package"

    def test_mutation_data_contains_reason(self):
        payload = {
            "wp_id": "wp-abc-123",
            "project_id": "proj-001",
            "reason": "ws_index is non-empty",
        }
        result = build_audit_event(
            event_type="ws_proposal_rejected",
            entity_id="wp-abc-123",
            entity_type="work_package",
            mutation_data=payload,
        )
        assert result["mutation_data"]["reason"] == "ws_index is non-empty"


# ===========================================================================
# ws_proposed
# ===========================================================================


class TestWsProposed:
    """ws_proposed — emitted per WS successfully persisted."""

    def test_produces_valid_event_dict(self):
        result = build_audit_event(
            event_type="ws_proposed",
            entity_id="ws-xyz-001",
            entity_type="work_statement",
            mutation_data={
                "ws_id": "ws-xyz-001",
                "wp_id": "wp-abc-123",
                "project_id": "proj-001",
            },
        )
        assert result["event_type"] == "ws_proposed"
        assert result["entity_id"] == "ws-xyz-001"
        assert result["entity_type"] == "work_statement"

    def test_mutation_data_contains_ws_id(self):
        payload = {
            "ws_id": "ws-xyz-001",
            "wp_id": "wp-abc-123",
            "project_id": "proj-001",
        }
        result = build_audit_event(
            event_type="ws_proposed",
            entity_id="ws-xyz-001",
            entity_type="work_statement",
            mutation_data=payload,
        )
        assert result["mutation_data"]["ws_id"] == "ws-xyz-001"
        assert result["mutation_data"]["wp_id"] == "wp-abc-123"
        assert result["mutation_data"]["project_id"] == "proj-001"


# ===========================================================================
# wp_ws_index_updated
# ===========================================================================


class TestWpWsIndexUpdated:
    """wp_ws_index_updated — emitted when WP ws_index is updated after proposal."""

    def test_produces_valid_event_dict(self):
        result = build_audit_event(
            event_type="wp_ws_index_updated",
            entity_id="wp-abc-123",
            entity_type="work_package",
            mutation_data={
                "wp_id": "wp-abc-123",
                "before_count": 0,
                "after_count": 3,
                "ws_ids": ["ws-001", "ws-002", "ws-003"],
            },
        )
        assert result["event_type"] == "wp_ws_index_updated"
        assert result["entity_id"] == "wp-abc-123"
        assert result["entity_type"] == "work_package"

    def test_mutation_data_contains_before_after_counts(self):
        payload = {
            "wp_id": "wp-abc-123",
            "before_count": 2,
            "after_count": 5,
            "ws_ids": ["ws-001", "ws-002", "ws-003", "ws-004", "ws-005"],
        }
        result = build_audit_event(
            event_type="wp_ws_index_updated",
            entity_id="wp-abc-123",
            entity_type="work_package",
            mutation_data=payload,
        )
        assert result["mutation_data"]["before_count"] == 2
        assert result["mutation_data"]["after_count"] == 5
        assert len(result["mutation_data"]["ws_ids"]) == 5


# ===========================================================================
# Common fields across all proposal event types
# ===========================================================================


class TestProposalEventsCommonFields:
    """All proposal events include timestamp, actor, entity_id, entity_type."""

    @pytest.mark.parametrize("event_type", sorted(PROPOSAL_EVENT_TYPES))
    def test_all_events_include_timestamp(self, event_type):
        result = build_audit_event(
            event_type=event_type,
            entity_id="test-id",
            entity_type="test-type",
            mutation_data={"key": "value"},
        )
        assert "timestamp" in result
        # Must be valid ISO format
        parsed = datetime.fromisoformat(result["timestamp"])
        assert parsed.tzinfo == timezone.utc

    @pytest.mark.parametrize("event_type", sorted(PROPOSAL_EVENT_TYPES))
    def test_all_events_include_actor(self, event_type):
        result = build_audit_event(
            event_type=event_type,
            entity_id="test-id",
            entity_type="test-type",
            mutation_data={},
        )
        assert "actor" in result
        assert result["actor"] == "system"

    @pytest.mark.parametrize("event_type", sorted(PROPOSAL_EVENT_TYPES))
    def test_all_events_include_entity_id(self, event_type):
        result = build_audit_event(
            event_type=event_type,
            entity_id="entity-42",
            entity_type="test-type",
            mutation_data={},
        )
        assert result["entity_id"] == "entity-42"

    @pytest.mark.parametrize("event_type", sorted(PROPOSAL_EVENT_TYPES))
    def test_all_events_include_entity_type(self, event_type):
        result = build_audit_event(
            event_type=event_type,
            entity_id="test-id",
            entity_type="work_package",
            mutation_data={},
        )
        assert result["entity_type"] == "work_package"

    @pytest.mark.parametrize("event_type", sorted(PROPOSAL_EVENT_TYPES))
    def test_custom_actor_preserved(self, event_type):
        result = build_audit_event(
            event_type=event_type,
            entity_id="test-id",
            entity_type="test-type",
            mutation_data={},
            actor="proposal_station",
        )
        assert result["actor"] == "proposal_station"
