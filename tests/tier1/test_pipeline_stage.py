"""Tests for PipelineStage model (WS-REWIND-001)."""

import pytest

from app.domain.models.pipeline_stage import PipelineStage


class TestStageOrdering:
    """Stage ordering must match the canonical pipeline: CI→PD→TA→IP→WP→WS."""

    def test_ci_is_first(self):
        assert PipelineStage.CI.order == 0

    def test_ws_is_last(self):
        assert PipelineStage.WS.order == 5

    def test_canonical_order(self):
        ordered = PipelineStage.all_stages_ordered()
        names = [s.name for s in ordered]
        assert names == ["CI", "PD", "TA", "IP", "WP", "WS"]

    def test_exactly_six_stages(self):
        assert len(list(PipelineStage)) == 6


class TestDownstreamUpstream:
    """Relationship queries between stages."""

    def test_pd_is_downstream_of_ci(self):
        assert PipelineStage.PD.is_downstream_of(PipelineStage.CI)

    def test_ci_is_not_downstream_of_pd(self):
        assert not PipelineStage.CI.is_downstream_of(PipelineStage.PD)

    def test_ws_is_downstream_of_all(self):
        for stage in PipelineStage:
            if stage != PipelineStage.WS:
                assert PipelineStage.WS.is_downstream_of(stage)

    def test_ci_is_upstream_of_all(self):
        for stage in PipelineStage:
            if stage != PipelineStage.CI:
                assert PipelineStage.CI.is_upstream_of(stage)

    def test_stage_not_downstream_of_itself(self):
        for stage in PipelineStage:
            assert not stage.is_downstream_of(stage)

    def test_stage_not_upstream_of_itself(self):
        for stage in PipelineStage:
            assert not stage.is_upstream_of(stage)


class TestDownstreamStages:
    """downstream_stages() returns all strictly later stages."""

    def test_ta_downstream_stages(self):
        result = PipelineStage.TA.downstream_stages()
        assert [s.name for s in result] == ["IP", "WP", "WS"]

    def test_ws_has_no_downstream(self):
        assert PipelineStage.WS.downstream_stages() == []

    def test_ci_downstream_is_everything_else(self):
        result = PipelineStage.CI.downstream_stages()
        assert len(result) == 5
        assert result[0] == PipelineStage.PD
        assert result[-1] == PipelineStage.WS


class TestStagesAtAndAfter:
    """stages_at_and_after() returns this stage plus all downstream (invalidation set)."""

    def test_ta_invalidation_set(self):
        result = PipelineStage.TA.stages_at_and_after()
        assert [s.name for s in result] == ["TA", "IP", "WP", "WS"]

    def test_ci_invalidation_set_is_full_pipeline(self):
        result = PipelineStage.CI.stages_at_and_after()
        assert len(result) == 6

    def test_ws_invalidation_set_is_just_ws(self):
        result = PipelineStage.WS.stages_at_and_after()
        assert [s.name for s in result] == ["WS"]


class TestDocTypeMapping:
    """Each stage maps to a document type ID."""

    def test_ci_doc_type(self):
        assert PipelineStage.CI.doc_type_id == "concierge_intake"

    def test_ta_doc_type(self):
        assert PipelineStage.TA.doc_type_id == "technical_architecture"

    def test_ws_doc_type(self):
        assert PipelineStage.WS.doc_type_id == "work_statement"

    def test_from_doc_type_id(self):
        assert PipelineStage.from_doc_type_id("project_discovery") == PipelineStage.PD

    def test_from_doc_type_id_invalid(self):
        with pytest.raises(ValueError, match="No pipeline stage"):
            PipelineStage.from_doc_type_id("nonexistent_type")

    def test_all_doc_type_ids_unique(self):
        ids = [s.doc_type_id for s in PipelineStage]
        assert len(ids) == len(set(ids))


class TestDisplayName:
    """Human-readable names."""

    def test_ci_display_name(self):
        assert PipelineStage.CI.display_name == "Concierge Intake"

    def test_all_have_display_names(self):
        for stage in PipelineStage:
            assert len(stage.display_name) > 0


class TestPGCIsNotAStage:
    """PGC is cross-cutting, not a rewind target."""

    def test_pgc_not_in_enum(self):
        names = [s.name for s in PipelineStage]
        assert "PGC" not in names

    def test_pgc_doc_type_not_mapped(self):
        with pytest.raises(ValueError):
            PipelineStage.from_doc_type_id("pgc")
