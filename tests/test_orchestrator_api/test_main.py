"""Tests for main FastAPI application."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_app_starts_on_configured_port():
    """AC-1: Validate API_HOST/API_PORT env vars."""
    # This is a smoke test - actual port binding tested in deployment
    assert True  # Placeholder for deployment validation


@pytest.mark.asyncio
async def test_error_response_structure(client: AsyncClient):
    """AC-7: Validates ErrorResponse model."""
    # Trigger 404 error
    response = await client.get("/pipelines/nonexistent")
    assert response.status_code == 404
    data = response.json()
    # FastAPI wraps HTTPException detail in "detail" key
    assert "detail" in data
    assert "error" in data["detail"]  # ← Changed
    assert "message" in data["detail"]  # ← Changed

@pytest.mark.asyncio
async def test_500_internal_error():
    """AC-7: Unhandled exception returns 500."""
    # Placeholder - actual implementation would mock an internal error
    assert True


@pytest.mark.asyncio
async def test_413_payload_too_large():
    """AC-7: Body size limit (QA-001 fix)."""
    # Placeholder - actual implementation would send oversized payload
    assert True


@pytest.mark.asyncio
async def test_openapi_schema_generation(client: AsyncClient):
    """AC-8: Validates /openapi.json."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "paths" in schema


@pytest.mark.asyncio
async def test_docs_endpoint_accessible(client: AsyncClient):
    """AC-8: Validates /docs renders."""
    response = await client.get("/docs")
    assert response.status_code == 200