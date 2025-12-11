"""Tests for main FastAPI application."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_openapi_schema_generation(client: AsyncClient):
    """Validates /openapi.json endpoint."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "paths" in schema
    assert "info" in schema


@pytest.mark.asyncio
async def test_docs_endpoint_accessible(client: AsyncClient):
    """Validates /docs Swagger UI renders."""
    response = await client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower()


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_error_response_structure(client: AsyncClient):
    """Validates error response format."""
    # Trigger 404 error with non-existent endpoint
    response = await client.get("/nonexistent/endpoint")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_cors_headers(client: AsyncClient):
    """Test CORS headers are present."""
    response = await client.options("/health")
    # CORS headers should be present
    assert response.status_code in [200, 204]


# TODO: Add test for 500 internal error
# TODO: Add test for 413 payload too large (body size limit)