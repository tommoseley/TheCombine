"""Tests for authentication middleware."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_401_unauthorized(client: AsyncClient):
    """AC-7, AC-11: Missing API key returns 401."""
    response = await client.post("/pipelines", json={"epic_id": "TEST-001"})
    assert response.status_code == 401
    data = response.json()
    assert data["error"] == "unauthorized"


@pytest.mark.asyncio
async def test_auth_required_on_post_endpoints(client: AsyncClient, auth_headers):
    """AC-11: All POST endpoints require auth."""
    # Test each POST endpoint
    endpoints = [
        ("/pipelines", {"epic_id": "TEST-001"}),
        ("/reset", {}),
    ]
    
    for path, body in endpoints:
        # Without auth - should fail
        response = await client.post(path, json=body)
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_valid_api_key_succeeds(client: AsyncClient, auth_headers):
    """AC-11: Valid API key allows access."""
    response = await client.post(
        "/pipelines",
        json={"epic_id": "TEST-001"},
        headers=auth_headers
    )
    assert response.status_code in [200, 201]  # Success or created


@pytest.mark.asyncio
async def test_invalid_api_key_rejected(client: AsyncClient):
    """AC-11: Invalid API key rejected."""
    response = await client.post(
        "/pipelines",
        json={"epic_id": "TEST-001"},
        headers={"X-API-Key": "invalid-key"}
    )
    assert response.status_code == 401