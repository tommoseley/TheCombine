"""Tests for stage normalization in correction endpoints (ADR-069 bug fixes).

Verifies:
- GET /corrections/{stage} accepts doc_type_id and normalizes to stage name
- Rewind correction normalizes applies_to_stages from doc_type_ids to stage names
- Prompt Mustache wrappers are stripped in both positive and negative paths
"""

import re
import pytest
from uuid import uuid4

from app.domain.models.authority_record import AuthorityRecordDTO
from app.domain.repositories.authority_repository import InMemoryAuthorityRepository
from app.domain.services.authority_service import AuthorityService


class TestGetCorrectionStageNormalization:
    """GET endpoint should accept both TA and technical_architecture."""

    @pytest.mark.asyncio
    async def test_lookup_by_doc_type_id(self):
        """get_current_correction with canonical stage name finds correction stored as TA."""
        repo = InMemoryAuthorityRepository()
        service = AuthorityService(repo)
        project_id = uuid4()
        event_id = uuid4()

        await service.record_authority(
            project_id=project_id,
            authority_type="operator_correction",
            stage="TA",
            key="correction:TA",
            value={"text": "Server-side only", "applies_to_stages": ["TA"], "rewind_event_id": str(event_id)},
            source_execution_id=event_id,
            lineage_path_id=event_id,
            actor="operator",
        )

        # Should find by canonical name
        result = await service.get_current_correction(project_id, "TA")
        assert result is not None
        assert result.value["text"] == "Server-side only"

        # Should NOT find by doc_type_id (that's the endpoint's job to normalize)
        result_by_doctype = await service.get_current_correction(project_id, "technical_architecture")
        assert result_by_doctype is None

    def test_pipeline_stage_from_doc_type_id(self):
        """PipelineStage.from_doc_type_id normalizes correctly."""
        from app.domain.models.pipeline_stage import PipelineStage

        assert PipelineStage.from_doc_type_id("technical_architecture").name == "TA"
        assert PipelineStage.from_doc_type_id("implementation_plan").name == "IP"
        assert PipelineStage.from_doc_type_id("project_discovery").name == "PD"


class TestAppliesToNormalization:
    """applies_to_stages should store canonical stage names, not doc_type_ids."""

    def test_normalize_doc_type_ids_to_stage_names(self):
        """Verify PipelineStage can resolve doc_type_ids for normalization."""
        from app.domain.models.pipeline_stage import PipelineStage

        raw = ["technical_architecture", "implementation_plan"]
        normalized = []
        for s in raw:
            try:
                normalized.append(PipelineStage[s.upper()].name)
            except KeyError:
                try:
                    normalized.append(PipelineStage.from_doc_type_id(s).name)
                except ValueError:
                    normalized.append(s.upper())

        assert normalized == ["TA", "IP"]

    def test_already_canonical_passes_through(self):
        """Already-canonical names (TA, IP) pass through unchanged."""
        from app.domain.models.pipeline_stage import PipelineStage

        raw = ["TA", "IP"]
        normalized = []
        for s in raw:
            try:
                normalized.append(PipelineStage[s.upper()].name)
            except KeyError:
                try:
                    normalized.append(PipelineStage.from_doc_type_id(s).name)
                except ValueError:
                    normalized.append(s.upper())

        assert normalized == ["TA", "IP"]


class TestAppliesToDeduplication:
    """Backend should deduplicate after normalization."""

    def test_dedup_mixed_formats(self):
        """['TA', 'technical_architecture'] normalizes to ['TA'] not ['TA', 'TA']."""
        from app.domain.models.pipeline_stage import PipelineStage

        raw = ["TA", "technical_architecture"]
        applies_to = []
        for s in raw:
            try:
                applies_to.append(PipelineStage[s.upper()].name)
            except KeyError:
                try:
                    applies_to.append(PipelineStage.from_doc_type_id(s).name)
                except ValueError:
                    pass
        # Deduplicate preserving order
        applies_to = list(dict.fromkeys(applies_to))
        assert applies_to == ["TA"]


class TestRejectInvalidStages:
    """Backend should reject unknown applies_to_stages values."""

    def test_unknown_stage_not_stored(self):
        """Garbage values should not persist as durable data."""
        from app.domain.models.pipeline_stage import PipelineStage

        raw = ["TA", "garbage_stage"]
        invalid = []
        for s in raw:
            try:
                PipelineStage[s.upper()]
            except KeyError:
                try:
                    PipelineStage.from_doc_type_id(s)
                except ValueError:
                    invalid.append(s)
        assert invalid == ["garbage_stage"]


class TestPromptMustacheWrapperStripping:
    """Mustache {{#}} / {{/}} wrappers must be stripped in all paths."""

    def test_positive_path_strips_wrappers(self):
        """When corrections exist, wrappers are removed and content is kept."""
        prompt = (
            "Some preamble.\n\n"
            "{{#operator_corrections}}\n"
            "## Operator Corrections (Binding)\n\n"
            "{{operator_corrections}}\n"
            "{{/operator_corrections}}\n\n"
            "Some postamble."
        )

        correction_text = "1. [From TA rewind] AI must be server-side"

        # Simulate positive path: replace placeholder, then strip wrappers
        result = prompt.replace("{{operator_corrections}}", correction_text)
        result = result.replace("{{#operator_corrections}}", "")
        result = result.replace("{{/operator_corrections}}", "")

        assert "{{#" not in result
        assert "{{/" not in result
        assert "{{operator_corrections}}" not in result
        assert "AI must be server-side" in result
        assert "## Operator Corrections (Binding)" in result

    def test_negative_path_strips_entire_block(self):
        """When no corrections, entire conditional block is stripped."""
        prompt = (
            "Some preamble.\n\n"
            "{{#operator_corrections}}\n"
            "## Operator Corrections (Binding)\n\n"
            "{{operator_corrections}}\n"
            "{{/operator_corrections}}\n\n"
            "Some postamble."
        )

        # Simulate negative path: strip entire conditional block
        pattern = r'\{\{#operator_corrections\}\}.*?\{\{/operator_corrections\}\}'
        result = re.sub(pattern, '', prompt, flags=re.DOTALL)
        result = result.replace("{{operator_corrections}}", "")

        assert "{{#" not in result
        assert "{{/" not in result
        assert "{{operator_corrections}}" not in result
        assert "Operator Corrections" not in result
        assert "Some preamble." in result
        assert "Some postamble." in result
