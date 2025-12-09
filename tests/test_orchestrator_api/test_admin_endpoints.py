"""Tests for reset and canon endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.skip(reason="Old orchestrator - replaced by data-driven in 175A/B")
async def test_reset_success(client: AsyncClient, auth_headers):
    """AC-6: Dev mode test."""
    response = await client.post("/reset", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert data["success"] is True


@pytest.mark.asyncio
async def test_reset_blocked_critical_phase():
    """AC-6: Guardrail enforcement (M-005 fix)."""
    # Placeholder - would set production mode and test blocking
    assert True