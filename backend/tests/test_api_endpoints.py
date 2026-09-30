"""Tests for all REST API endpoints."""

import pytest
from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient):
    """GET /api/health must return 200 with standard health JSON."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "researchops-api",
    }


def test_research_endpoints_lifecycle(client: TestClient):
    """Test POST /api/research, GET /api/research, and GET /api/research/{id}."""
    payload = {
        "query": "Assess trauma center coverage and bed gaps in rural Appalachia",
        "region": "Appalachia",
        "parameters": {"depth": "standard"},
    }

    # Create research session
    create_res = client.post("/api/research", json=payload)
    assert create_res.status_code == 201
    data = create_res.json()
    assert "research_id" in data
    assert data["query"] == payload["query"]
    assert data["region"] == payload["region"]
    assert len(data["tasks"]) > 0
    research_id = data["research_id"]

    # List research sessions
    list_res = client.get("/api/research")
    assert list_res.status_code == 200
    all_sessions = list_res.json()
    assert any(s["research_id"] == research_id for s in all_sessions)

    # Get specific research session
    get_res = client.get(f"/api/research/{research_id}")
    assert get_res.status_code == 200
    assert get_res.json()["research_id"] == research_id

    # 404 for unknown research session
    not_found_res = client.get("/api/research/non-existent-id")
    assert not_found_res.status_code == 404


def test_sources_endpoints(client: TestClient):
    """Test GET /api/sources and 404 handling."""
    res = client.get("/api/sources")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    not_found = client.get("/api/sources/unknown-source-id")
    assert not_found.status_code == 404


def test_facilities_endpoints(client: TestClient):
    """Test GET /api/facilities and 404 handling."""
    res = client.get("/api/facilities")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    not_found = client.get("/api/facilities/unknown-facility-id")
    assert not_found.status_code == 404


def test_analysis_endpoints(client: TestClient):
    """Test GET /api/analysis, /api/analysis/conflicts, and /api/analysis/gaps."""
    overview_res = client.get("/api/analysis")
    assert overview_res.status_code == 200
    overview = overview_res.json()
    assert "total_conflicts" in overview
    assert "total_service_gaps" in overview
    assert "conflicts" in overview
    assert "service_gaps" in overview

    conflicts_res = client.get("/api/analysis/conflicts")
    assert conflicts_res.status_code == 200
    assert isinstance(conflicts_res.json(), list)

    gaps_res = client.get("/api/analysis/gaps")
    assert gaps_res.status_code == 200
    assert isinstance(gaps_res.json(), list)


def test_reports_endpoints(client: TestClient):
    """Test GET /api/reports and 404 handling."""
    res = client.get("/api/reports")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    not_found = client.get("/api/reports/unknown-report-id")
    assert not_found.status_code == 404


def test_research_validation_error(client: TestClient):
    """POST /api/research with short query should fail validation."""
    response = client.post("/api/research", json={"query": "hi"})
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
