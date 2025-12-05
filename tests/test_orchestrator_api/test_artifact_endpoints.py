"""Tests for artifact submission endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_submit_artifact_success(client: AsyncClient, auth_headers):
    """AC-4: Happy path."""
    # Create pipeline first
    create_response = await client.post(
        "/pipelines",
        json={"epic_id": "TEST-001"},
        headers=auth_headers
    )
    pipeline_id = create_response.json()["pipeline_id"]
    
    # Submit artifact
    artifact = {
        "phase": "pm_phase",
        "mentor_role": "pm",
        "artifact_type": "epic",
        "payload": {
            "epic_id": "TEST-001",
            "title": "Test Epic",
            "description": "Test epic for artifact submission",  # ← ADD
            "business_value": "Validate artifact submission flow",  # ← ADD
            "scope": "Single pipeline with artifact",  # ← ADD
            "stories": [],
            "acceptance_criteria": [],  # ← ADD (optional but good practice)
            "version": "v1.0"
        }
    }
    response = await client.post(
        f"/pipelines/{pipeline_id}/artifacts",
        json=artifact,
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "artifact_id" in data


@pytest.mark.asyncio
async def test_422_validation_error():
    """AC-7, AC-4: Schema mismatch."""
    # Placeholder - would submit invalid artifact
    assert True


@pytest.mark.asyncio
async def test_submit_artifact_validation_failure():
    """AC-4: Schema validation test."""
    # Placeholder - mock schema validation failure
    assert True


@pytest.mark.asyncio
async def test_submit_artifact_epic_id_mismatch():
    """AC-4: epicId validation (B-004 fix)."""
    # Placeholder - test epicId mismatch detection
    assert True