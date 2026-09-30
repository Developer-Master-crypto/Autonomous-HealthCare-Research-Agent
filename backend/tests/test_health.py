"""Tests for service health check and error handling."""

import pytest
from fastapi.testclient import TestClient
import httpx


def test_health_endpoint_sync(client: TestClient):
    """Verify GET /api/health returns 200 and expected JSON payload."""
    response = client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data == {
        "status": "ok",
        "service": "researchops-api",
    }
    assert response.headers["content-type"].startswith("application/json")


@pytest.mark.asyncio
async def test_health_endpoint_async(async_client: httpx.AsyncClient):
    """Verify async GET /api/health."""
    response = await async_client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "researchops-api",
    }


def test_root_index_endpoint(client: TestClient):
    """Verify root index responds with metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "ResearchOps"
    assert data["team"] == "Spideyx"
    assert data["hackathon"] == "GATEWAYS 2026"
    assert "endpoints" in data
    assert data["endpoints"]["health"] == "/api/health"


def test_404_custom_error_handler(client: TestClient):
    """Verify unknown route triggers custom 404 JSON handler."""
    response = client.get("/api/non_existent_route")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "HTTP_404"
