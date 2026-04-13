"""Tests for Rewind Impact Evaluator (WS-REWIND-003)."""

import pytest

from app.domain.models.pipeline_stage import PipelineStage
from app.domain.services.rewind_impact_evaluator import (
    evaluate_rewind_impact,
    evaluate_rewind_impact_safe,
    get_affected_doc_type_ids,
)


class TestEvaluateRewindImpact:
    """Core impact evaluation using linear model."""

    def test_rewind_at_ta_affects_ta_wp_ws(self):
        result = evaluate_rewind_impact(PipelineStage.TA)
        names = [s.name for s in result]
        assert names == ["TA", "WP", "WS"]

    def test_rewind_at_ci_affects_full_pipeline(self):
        result = evaluate_rewind_impact(PipelineStage.CI)
        assert len(result) == 6
        assert result[0] == PipelineStage.CI
        assert result[-1] == PipelineStage.WS

    def test_rewind_at_ws_affects_only_ws(self):
        result = evaluate_rewind_impact(PipelineStage.WS)
        assert [s.name for s in result] == ["WS"]

    def test_rewind_at_pd_affects_pd_through_ws(self):
        result = evaluate_rewind_impact(PipelineStage.PD)
        names = [s.name for s in result]
        assert names == ["PD", "IP", "TA", "WP", "WS"]

    def test_rewind_at_wp_affects_wp_and_ws(self):
        result = evaluate_rewind_impact(PipelineStage.WP)
        names = [s.name for s in result]
        assert names == ["WP", "WS"]

    def test_rewind_at_ip_affects_ip_ta_wp_ws(self):
        result = evaluate_rewind_impact(PipelineStage.IP)
        names = [s.name for s in result]
        assert names == ["IP", "TA", "WP", "WS"]

    def test_result_is_in_pipeline_order(self):
        result = evaluate_rewind_impact(PipelineStage.PD)
        orders = [s.order for s in result]
        assert orders == sorted(orders)


class TestEvaluateRewindImpactSafe:
    """Safe version with string input and conservative default."""

    def test_valid_stage_name(self):
        result = evaluate_rewind_impact_safe("TA")
        names = [s.name for s in result]
        assert names == ["TA", "WP", "WS"]

    def test_lowercase_stage_name(self):
        result = evaluate_rewind_impact_safe("ta")
        names = [s.name for s in result]
        assert names == ["TA", "WP", "WS"]

    def test_valid_doc_type_id(self):
        result = evaluate_rewind_impact_safe("technical_architecture")
        names = [s.name for s in result]
        assert names == ["TA", "WP", "WS"]

    def test_invalid_stage_conservative_default(self):
        result = evaluate_rewind_impact_safe("nonexistent")
        assert len(result) == 6  # full pipeline

    def test_pgc_triggers_conservative_default(self):
        result = evaluate_rewind_impact_safe("PGC")
        assert len(result) == 6  # PGC is not a stage


class TestGetAffectedDocTypeIds:
    """Returns doc_type_id strings for affected stages."""

    def test_ta_rewind_doc_types(self):
        result = get_affected_doc_type_ids(PipelineStage.TA)
        assert result == [
            "technical_architecture",
            "work_package",
            "work_statement",
        ]

    def test_ci_rewind_returns_all_doc_types(self):
        result = get_affected_doc_type_ids(PipelineStage.CI)
        assert len(result) == 7  # 6 stages + work_package_candidate
        assert result[0] == "concierge_intake"

    def test_ws_rewind_returns_single(self):
        result = get_affected_doc_type_ids(PipelineStage.WS)
        assert result == ["work_statement"]

    def test_ip_rewind_includes_work_package_candidate(self):
        """WPCs are derived from IP — must be invalidated when IP is affected."""
        result = get_affected_doc_type_ids(PipelineStage.IP)
        assert "work_package_candidate" in result
        assert "implementation_plan" in result

    def test_pd_rewind_includes_work_package_candidate(self):
        """PD rewind cascades through IP, so WPCs are also invalidated."""
        result = get_affected_doc_type_ids(PipelineStage.PD)
        assert "work_package_candidate" in result

    def test_ci_rewind_includes_work_package_candidate(self):
        """Full pipeline rewind includes WPCs."""
        result = get_affected_doc_type_ids(PipelineStage.CI)
        assert "work_package_candidate" in result

    def test_ta_rewind_does_not_include_work_package_candidate(self):
        """TA rewind does not invalidate WPCs — they come from IP, not TA."""
        result = get_affected_doc_type_ids(PipelineStage.TA)
        assert "work_package_candidate" not in result

    def test_wp_rewind_does_not_include_work_package_candidate(self):
        """WP rewind does not invalidate WPCs."""
        result = get_affected_doc_type_ids(PipelineStage.WP)
        assert "work_package_candidate" not in result
