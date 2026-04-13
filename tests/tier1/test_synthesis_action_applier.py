"""
WS-SYNTHESIS-005: Synthesis Action Applier Tests.

Validates:
- Each action type maps to correct pipeline stage
- Correction briefs are well-formed
- Post-condition verification works for REMOVE_WS and DEFER_COMPONENT
- Unknown action types raise ValueError
"""

import pytest
from app.domain.services.synthesis_action_applier import (
    action_to_correction,
    verify_post_condition,
    ACTION_STAGE_MAP,
    CorrectionBrief,
)


# =========================================================================
# Action-to-correction mapping
# =========================================================================


class TestActionToCorrection:
    def test_merge_ws_targets_work_statement_stage(self):
        action = {
            "action_type": "MERGE_WS",
            "targets": ["WS-138", "WS-145"],
            "rationale": "62% overlap",
            "post_condition": "count == 0",
        }
        brief = action_to_correction(action)
        assert brief.rewind_to_stage == "work_statement"
        assert brief.applies_to_stages == ["work_statement"]

    def test_split_ws_targets_work_statement_stage(self):
        action = {
            "action_type": "SPLIT_WS",
            "targets": ["WS-001"],
            "rationale": "mixed concerns",
            "post_condition": "count == 2",
        }
        brief = action_to_correction(action)
        assert brief.rewind_to_stage == "work_statement"

    def test_remove_ws_targets_work_statement_stage(self):
        action = {
            "action_type": "REMOVE_WS",
            "targets": ["WS-140"],
            "rationale": "redundant",
            "post_condition": "WS-140 not in binder",
        }
        brief = action_to_correction(action)
        assert brief.rewind_to_stage == "work_statement"

    def test_normalize_boundary_targets_work_statement_stage(self):
        action = {
            "action_type": "NORMALIZE_BOUNDARY",
            "targets": ["WS-001", "WS-002"],
            "rationale": "overlap",
            "post_condition": "overlap < 10%",
        }
        brief = action_to_correction(action)
        assert brief.rewind_to_stage == "work_statement"

    def test_defer_component_targets_ta_stage(self):
        action = {
            "action_type": "DEFER_COMPONENT",
            "targets": ["MediaReferenceManager"],
            "rationale": "no WP coverage",
            "post_condition": "component deferred",
        }
        brief = action_to_correction(action)
        assert brief.rewind_to_stage == "technical_architecture"

    def test_defer_component_cascades_to_downstream(self):
        action = {
            "action_type": "DEFER_COMPONENT",
            "targets": ["MediaReferenceManager"],
            "rationale": "no WP coverage",
            "post_condition": "component deferred",
        }
        brief = action_to_correction(action)
        assert "technical_architecture" in brief.applies_to_stages
        assert "work_package" in brief.applies_to_stages
        assert "work_statement" in brief.applies_to_stages

    def test_unknown_action_raises(self):
        action = {
            "action_type": "REWRITE_TA",
            "targets": ["TA-001"],
            "rationale": "test",
            "post_condition": "test",
        }
        with pytest.raises(ValueError, match="Unknown action type"):
            action_to_correction(action)

    def test_all_five_action_types_mapped(self):
        assert len(ACTION_STAGE_MAP) == 5
        expected = {"MERGE_WS", "SPLIT_WS", "REMOVE_WS", "NORMALIZE_BOUNDARY", "DEFER_COMPONENT"}
        assert set(ACTION_STAGE_MAP.keys()) == expected


# =========================================================================
# Correction brief content
# =========================================================================


class TestCorrectionBriefContent:
    def test_merge_brief_contains_targets(self):
        action = {
            "action_type": "MERGE_WS",
            "targets": ["WS-138", "WS-145"],
            "rationale": "storage overlap",
            "post_condition": "merged",
        }
        brief = action_to_correction(action)
        assert "WS-138" in brief.reason
        assert "WS-145" in brief.reason
        assert "MERGE_WS" in brief.reason

    def test_normalize_brief_contains_field_restriction(self):
        action = {
            "action_type": "NORMALIZE_BOUNDARY",
            "targets": ["WS-001"],
            "rationale": "overlap",
            "post_condition": "no overlap",
        }
        brief = action_to_correction(action)
        assert "Do NOT change objective" in brief.reason

    def test_defer_brief_says_not_remove(self):
        action = {
            "action_type": "DEFER_COMPONENT",
            "targets": ["X"],
            "rationale": "test",
            "post_condition": "deferred",
        }
        brief = action_to_correction(action)
        assert "Do not remove" in brief.reason
        assert "deferred" in brief.reason.lower()

    def test_brief_preserves_source(self):
        action = {
            "action_type": "SPLIT_WS",
            "targets": ["WS-001"],
            "rationale": "mixed concerns",
            "post_condition": "count == 2",
        }
        brief = action_to_correction(action)
        assert brief.source_action_type == "SPLIT_WS"
        assert brief.source_targets == ["WS-001"]
        assert brief.post_condition == "count == 2"


# =========================================================================
# Post-condition verification
# =========================================================================


class TestPostConditionVerification:
    def test_remove_ws_passes_when_target_absent(self):
        action = {
            "action_type": "REMOVE_WS",
            "targets": ["WS-140"],
            "post_condition": "WS-140 not present",
        }
        content = {"work_statements": ["WS-136", "WS-137"]}
        assert verify_post_condition(action, content) is True

    def test_remove_ws_fails_when_target_present(self):
        action = {
            "action_type": "REMOVE_WS",
            "targets": ["WS-140"],
            "post_condition": "WS-140 not present",
        }
        content = {"work_statements": ["WS-140", "WS-136"]}
        assert verify_post_condition(action, content) is False

    def test_defer_component_passes_when_deferred(self):
        action = {
            "action_type": "DEFER_COMPONENT",
            "targets": ["MediaReferenceManager"],
            "post_condition": "component deferred",
        }
        content = {
            "mvp_scope": {
                "included": ["VoiceInputController"],
                "deferred": ["MediaReferenceManager"],
            }
        }
        assert verify_post_condition(action, content) is True

    def test_defer_component_fails_when_not_deferred(self):
        action = {
            "action_type": "DEFER_COMPONENT",
            "targets": ["MediaReferenceManager"],
            "post_condition": "component deferred",
        }
        content = {
            "mvp_scope": {
                "included": ["VoiceInputController", "MediaReferenceManager"],
                "deferred": [],
            }
        }
        assert verify_post_condition(action, content) is False

    def test_merge_ws_returns_true_inconclusive(self):
        action = {
            "action_type": "MERGE_WS",
            "targets": ["WS-138", "WS-145"],
            "post_condition": "merged into single WS",
        }
        content = {}
        assert verify_post_condition(action, content) is True
