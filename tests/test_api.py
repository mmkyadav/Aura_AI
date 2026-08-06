"""
tests/test_api.py
-----------------
API endpoint tests for Aura REST service.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test /api/v1/health endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Aura" in data["app"]


@pytest.mark.asyncio
async def test_create_thread():
    """Test creating a thread for a user."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/users/user_123/threads", json={"title": "Test Chat"})
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "user_123"
    assert "thread_id" in data
    assert data["title"] == "Test Chat"
