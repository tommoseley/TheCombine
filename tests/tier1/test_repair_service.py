"""Tier-1 tests for repair service (WS-REPAIR-002, ADR-065).

Tests prompt building, output validation, and proposal generation.
"""

import json
import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from app.domain.services.cross_layer_evaluator import TAOwnsValidationFinding
from app.domain.services.repair_service import (
    build_repair_prompt,
    validate_repair_output,
    generate_repair_proposal,
)
from app.domain.repositories.repair_proposal_repository import (
    InMemoryRepairProposalRepository,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _finding(name="API Gateway", issue="missing_owns"):
    return TAOwnsValidationFinding(
        component_name=name,
        issue_type=issue,
        severity="advisory",
        message=f"Component '{name}' has no 'owns' field",
    )


def _component(name="API Gateway", owns=None):
    comp = {"name": name, "purpose": "Handles API requests"}
    if owns is not None:
        comp["owns"] = owns
    return comp


# ---------------------------------------------------------------------------
# build_repair_prompt
# ---------------------------------------------------------------------------

class TestBuildRepairPrompt:
    def test_prompt_contains_component(self):
        prompt = build_repair_prompt(
            component=_component(),
            finding=_finding(),
            ta_context=[_component(), _component("Data Store", ["src/db/"])],
        )
        assert "API Gateway" in prompt
        assert "missing_owns" in prompt

    def test_prompt_excludes_target_from_context(self):
        prompt = build_repair_prompt(
            component=_component(),
            finding=_finding(),
            ta_context=[_component(), _component("Data Store", ["src/db/"])],
        )
        # Context should only contain Data Store, not API Gateway
        assert "Data Store" in prompt

    def test_prompt_includes_finding(self):
        prompt = build_repair_prompt(
            component=_component(),
            finding=_finding(),
            ta_context=[],
        )
        assert "missing_owns" in prompt
        assert "advisory" in prompt


# ---------------------------------------------------------------------------
# validate_repair_output
# ---------------------------------------------------------------------------

class TestValidateRepairOutput:
    def test_valid_output(self):
        original = _component()
        output = {"name": "API Gateway", "purpose": "Handles API requests", "owns": ["src/api/"]}
        errors = validate_repair_output(output, original)
        assert errors == []

    def test_name_changed(self):
        original = _component()
        output = {"name": "Changed Name", "owns": ["src/api/"]}
        errors = validate_repair_output(output, original)
        assert any("name changed" in e.lower() for e in errors)

    def test_empty_owns(self):
        original = _component()
        output = {"name": "API Gateway", "owns": []}
        errors = validate_repair_output(output, original)
        assert any("empty" in e.lower() for e in errors)

    def test_missing_owns(self):
        original = _component()
        output = {"name": "API Gateway"}
        errors = validate_repair_output(output, original)
        assert any("empty" in e.lower() or "missing" in e.lower() for e in errors)

    def test_whitespace_only_owns(self):
        original = _component()
        output = {"name": "API Gateway", "owns": ["  ", ""]}
        errors = validate_repair_output(output, original)
        assert any("blank" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# generate_repair_proposal
# ---------------------------------------------------------------------------

class TestGenerateRepairProposal:
    @pytest.fixture
    def repo(self):
        return InMemoryRepairProposalRepository()

    @pytest.fixture
    def mock_llm(self):
        client = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_generates_valid_proposal(self, repo, mock_llm):
        """Valid LLM output produces a pending proposal."""
        mock_llm.complete.return_value = json.dumps({
            "name": "API Gateway",
            "purpose": "Handles API requests",
            "owns": ["src/api/", "src/routes/"],
        })

        proposal = await generate_repair_proposal(
            artifact_id=uuid4(),
            component=_component(),
            finding=_finding(),
            ta_components=[_component()],
            llm_client=mock_llm,
            repo=repo,
        )

        assert proposal is not None
        assert proposal.status == "pending"
        assert proposal.artifact_type == "TA"
        assert proposal.component_identifier == "API Gateway"
        assert proposal.proposed_payload["owns"] == ["src/api/", "src/routes/"]

    @pytest.mark.asyncio
    async def test_persists_to_repo(self, repo, mock_llm):
        """Proposal is persisted to repository."""
        mock_llm.complete.return_value = json.dumps({
            "name": "API Gateway",
            "owns": ["src/api/"],
        })

        proposal = await generate_repair_proposal(
            artifact_id=uuid4(),
            component=_component(),
            finding=_finding(),
            ta_components=[],
            llm_client=mock_llm,
            repo=repo,
        )

        retrieved = await repo.get_by_id(proposal.id)
        assert retrieved is not None

    @pytest.mark.asyncio
    async def test_rejects_invalid_json(self, repo, mock_llm):
        """Non-JSON LLM output returns None."""
        mock_llm.complete.return_value = "This is not JSON at all"

        proposal = await generate_repair_proposal(
            artifact_id=uuid4(),
            component=_component(),
            finding=_finding(),
            ta_components=[],
            llm_client=mock_llm,
            repo=repo,
        )

        assert proposal is None
        results = await repo.get_by_artifact(uuid4())
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_rejects_empty_owns(self, repo, mock_llm):
        """LLM output with empty owns is rejected."""
        mock_llm.complete.return_value = json.dumps({
            "name": "API Gateway",
            "owns": [],
        })

        proposal = await generate_repair_proposal(
            artifact_id=uuid4(),
            component=_component(),
            finding=_finding(),
            ta_components=[],
            llm_client=mock_llm,
            repo=repo,
        )

        assert proposal is None

    @pytest.mark.asyncio
    async def test_rejects_name_change(self, repo, mock_llm):
        """LLM output that changes component name is rejected."""
        mock_llm.complete.return_value = json.dumps({
            "name": "Different Gateway",
            "owns": ["src/api/"],
        })

        proposal = await generate_repair_proposal(
            artifact_id=uuid4(),
            component=_component(),
            finding=_finding(),
            ta_components=[],
            llm_client=mock_llm,
            repo=repo,
        )

        assert proposal is None

    @pytest.mark.asyncio
    async def test_no_full_ta_rewrite(self, mock_llm, repo):
        """LLM is called with single component, not full TA."""
        mock_llm.complete.return_value = json.dumps({
            "name": "API Gateway",
            "owns": ["src/api/"],
        })

        await generate_repair_proposal(
            artifact_id=uuid4(),
            component=_component(),
            finding=_finding(),
            ta_components=[_component(), _component("Store")],
            llm_client=mock_llm,
            repo=repo,
        )

        # Verify the prompt was called with single component context
        call_args = mock_llm.complete.call_args
        messages = call_args.kwargs.get("messages") or call_args.args[0]
        prompt = messages[0]["content"]
        # Prompt should contain single component, not "components" array
        assert "API Gateway" in prompt
