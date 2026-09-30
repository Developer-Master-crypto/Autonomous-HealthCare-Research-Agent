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


def test_security_headers_and_default_cors_are_restricted(client: TestClient):
    response = client.get("/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "*" not in response.headers.get("access-control-allow-origin", "")


def test_research_endpoint_has_per_client_rate_limit(monkeypatch):
    from backend.app.core.config import settings
    from backend.app.main import create_app

    monkeypatch.setattr(settings, "RESEARCH_RATE_LIMIT_PER_MINUTE", 1)
    with TestClient(create_app()) as limited_client:
        first = limited_client.post("/api/research", json={"query": "Assess cardiac access"})
        second = limited_client.post("/api/research", json={"query": "Assess cardiac access"})
    assert first.status_code == 201
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "RATE_LIMITED"


def test_cors_configuration_rejects_wildcard_origins():
    from pydantic import ValidationError
    from backend.app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(ALLOWED_ORIGINS="*")
