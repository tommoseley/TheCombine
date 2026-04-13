"""
WS-SYNTHESIS-003: Synthesis Service Tests.

Validates:
- Finding extraction from LLM output
- Canonical normalization keys
- Agreement scoring (both flagged = high, one = moderate)
- Lane classification (actions vs questions)
- Merged output structure
"""

import pytest
from app.domain.services.synthesis_service import (
    SynthesisFinding,
    _extract_findings,
    _normalize_key,
    _merge_findings,
)


# =========================================================================
# Fixtures
# =========================================================================


def _instance_output(actions=None, questions=None):
    return {
        "project_id": "test",
        "binder_document_count": 10,
        "instance_a_finding_count": 0,
        "instance_b_finding_count": 0,
        "agreement_count": 0,
        "actions": actions or [],
        "questions": questions or [],
    }


def _action(action_type="MERGE_WS", targets=None, **kwargs):
    a = {
        "action_type": action_type,
        "targets": targets or ["WS-001", "WS-002"],
        "rationale": "Test rationale",
        "post_condition": "test condition",
    }
    a.update(kwargs)
    return a


def _question(lens="platform_realism", artifacts=None, **kwargs):
    q = {
        "finding_id": "F-001",
        "lens": lens,
        "severity": "should_fix",
        "artifacts": artifacts or ["TA-001"],
        "question": "Test question?",
        "confidence": "moderate",
    }
    q.update(kwargs)
    return q


# =========================================================================
# Finding extraction
# =========================================================================


class TestExtractFindings:
    def test_extracts_actions(self):
        output = _instance_output(actions=[_action()])
        findings = _extract_findings(output)
        assert len(findings) == 1
        assert findings[0].finding_type == "action"
        assert findings[0].action_type == "MERGE_WS"
        assert findings[0].target_ids == frozenset(["WS-001", "WS-002"])

    def test_extracts_questions(self):
        output = _instance_output(questions=[_question()])
        findings = _extract_findings(output)
        assert len(findings) == 1
        assert findings[0].finding_type == "question"
        assert findings[0].lens == "platform_realism"
        assert findings[0].target_ids == frozenset(["TA-001"])

    def test_extracts_mixed(self):
        output = _instance_output(
            actions=[_action()],
            questions=[_question(), _question(lens="mvp_discipline")],
        )
        findings = _extract_findings(output)
        assert len(findings) == 3
        assert sum(1 for f in findings if f.finding_type == "action") == 1
        assert sum(1 for f in findings if f.finding_type == "question") == 2

    def test_empty_output(self):
        output = _instance_output()
        findings = _extract_findings(output)
        assert findings == []


# =========================================================================
# Normalization keys
# =========================================================================


class TestNormalizeKey:
    def test_action_key(self):
        f = SynthesisFinding(
            finding_type="action",
            action_type="MERGE_WS",
            lens=None,
            target_ids=frozenset(["WS-001", "WS-002"]),
            raw={},
        )
        key = _normalize_key(f)
        assert key == ("action", "MERGE_WS", frozenset(["WS-001", "WS-002"]))

    def test_question_key(self):
        f = SynthesisFinding(
            finding_type="question",
            action_type=None,
            lens="platform_realism",
            target_ids=frozenset(["TA-001"]),
            raw={},
        )
        key = _normalize_key(f)
        assert key == ("question", "platform_realism", frozenset(["TA-001"]))

    def test_target_order_does_not_matter(self):
        f1 = SynthesisFinding(
            finding_type="action",
            action_type="MERGE_WS",
            lens=None,
            target_ids=frozenset(["WS-002", "WS-001"]),
            raw={},
        )
        f2 = SynthesisFinding(
            finding_type="action",
            action_type="MERGE_WS",
            lens=None,
            target_ids=frozenset(["WS-001", "WS-002"]),
            raw={},
        )
        assert _normalize_key(f1) == _normalize_key(f2)


# =========================================================================
# Agreement scoring
# =========================================================================


class TestMergeFindings:
    def test_both_flagged_high_confidence(self):
        action = _action(targets=["WS-001", "WS-002"])
        fa = _extract_findings(_instance_output(actions=[action]))
        fb = _extract_findings(_instance_output(actions=[action]))
        merged = _merge_findings(fa, fb)
        assert len(merged) == 1
        assert merged[0]["confidence"] == "high"

    def test_one_flagged_moderate_confidence(self):
        action = _action(targets=["WS-001", "WS-002"])
        fa = _extract_findings(_instance_output(actions=[action]))
        fb = _extract_findings(_instance_output())  # no findings
        merged = _merge_findings(fa, fb)
        assert len(merged) == 1
        assert merged[0]["confidence"] == "moderate"

    def test_different_findings_both_moderate(self):
        a1 = _action(action_type="MERGE_WS", targets=["WS-001", "WS-002"])
        a2 = _action(action_type="REMOVE_WS", targets=["WS-003"])
        fa = _extract_findings(_instance_output(actions=[a1]))
        fb = _extract_findings(_instance_output(actions=[a2]))
        merged = _merge_findings(fa, fb)
        assert len(merged) == 2
        assert all(m["confidence"] == "moderate" for m in merged)

    def test_mixed_agreement_and_disagreement(self):
        shared = _action(targets=["WS-001", "WS-002"])
        only_a = _question(lens="platform_realism", artifacts=["TA-001"])
        only_b = _question(lens="mvp_discipline", artifacts=["WS-005"])

        fa = _extract_findings(_instance_output(actions=[shared], questions=[only_a]))
        fb = _extract_findings(_instance_output(actions=[shared], questions=[only_b]))
        merged = _merge_findings(fa, fb)
        assert len(merged) == 3

        confidences = {m["raw"].get("action_type") or m["raw"].get("lens"): m["confidence"] for m in merged}
        assert confidences["MERGE_WS"] == "high"
        assert confidences["platform_realism"] == "moderate"
        assert confidences["mvp_discipline"] == "moderate"

    def test_empty_both(self):
        merged = _merge_findings([], [])
        assert merged == []


# =========================================================================
# Lane classification
# =========================================================================


class TestLaneClassification:
    def test_actions_in_action_lane(self):
        action = _action()
        fa = _extract_findings(_instance_output(actions=[action]))
        merged = _merge_findings(fa, [])
        assert all(m["finding_type"] == "action" for m in merged)

    def test_questions_in_question_lane(self):
        question = _question()
        fa = _extract_findings(_instance_output(questions=[question]))
        merged = _merge_findings(fa, [])
        assert all(m["finding_type"] == "question" for m in merged)

    def test_confidence_stamped_on_raw(self):
        action = _action()
        fa = _extract_findings(_instance_output(actions=[action]))
        fb = _extract_findings(_instance_output(actions=[action]))
        merged = _merge_findings(fa, fb)
        assert merged[0]["raw"]["confidence"] == "high"
