"""HTTP-level end-to-end coverage using explicitly labelled synthetic providers."""

import importlib

import pytest
from fastapi.testclient import TestClient

from backend.app.db.connection import MockDatabaseClient
from backend.app.repositories.source_repository import SourceRepository
from backend.app.schemas.research import ResearchTask
from backend.app.services.content_extractor import ContentExtractor
from backend.app.services.geocoding_provider import MockGeocodingProvider
from backend.app.services.geographic_service import GeographicService
from backend.app.services.research_orchestrator import ResearchOrchestrator
from backend.app.services.source_fetcher import FetchResult, FetchStatus

QUERY = "Analyze cardiac healthcare infrastructure within 10 km of Whitefield and identify potential service gaps."


class FixtureSearch:
    async def search_task(self, task: ResearchTask):
        return [
            _result("https://mock-source.invalid/provider-a", "Cardiac provider listing"),
            _result("https://mock-source.invalid/provider-b", "Cardiac provider notice"),
        ]


def _result(url, title):
    from backend.app.schemas.search import SearchResult
    return SearchResult(title=title, url=url, domain="mock-source.invalid")


class FixtureFetcher:
    async def fetch(self, url):
        positive = "provider-a" in url
        text = ("Mock Cardiac Hospital offers cardiology services. Address: 1 Demo Road. City: Whitefield. "
                "Latitude: 12.9700 Longitude: 77.7500" if positive else
                "Mock Cardiac Hospital does not offer cardiology services. Address: 1 Demo Road. City: Whitefield. "
                "Latitude: 12.9700 Longitude: 77.7500")
        return FetchResult(url, url, FetchStatus.SUCCESS,
                           content=f"<html><title>{'Provider A' if positive else 'Provider B'}</title><main>{text}</main></html>",
                           content_type="text/html")


@pytest.mark.asyncio
async def test_complete_research_pipeline_ids_traceability_and_database(monkeypatch):
    db = MockDatabaseClient()
    sources = SourceRepository(db)
    orchestrator = ResearchOrchestrator(
        search_service=FixtureSearch(),
        content_extractor=ContentExtractor(FixtureFetcher(), sources),
        geographic_service=GeographicService(
            geocoding_provider=MockGeocodingProvider(known_locations={"whitefield": (12.9698, 77.75)})),
        database_client=db,
        execution_mode="mock",
        max_tasks=2,
    )
    api_module = importlib.import_module("backend.app.api.research")
    monkeypatch.setattr(api_module, "research_orchestrator", orchestrator)

    with TestClient(importlib.import_module("backend.app.main").app) as client:
        response = client.post("/api/research", json={"query": QUERY})
        assert response.status_code == 201, response.text
        project = response.json()
        research_id = project["research_id"]
        assert project["region"] == "Whitefield"
        assert project["execution_mode"] == "mock"
        assert project["progress"]["current_stage"] == "COMPLETED"
        assert project["progress"]["completed_stages"] == [
            "SEARCH", "SOURCE EXTRACTION", "FACILITY/SERVICE EXTRACTION", "EVIDENCE COLLECTION",
            "EVIDENCE VERIFICATION", "CONFLICT DETECTION", "GEOGRAPHIC ANALYSIS",
            "SERVICE GAP ANALYSIS", "REPORT GENERATION",
        ]
        assert all(task["research_id"] == research_id for task in project["tasks"])
        assert project["intermediate_results"]["geographic_analysis"]["radius_km"] == 10
        assert project["intermediate_results"]["geographic_analysis"]["summary"]["inside_radius"] > 0
        assert project["intermediate_results"]["persistence_status"] == "mock_memory"

        report_response = client.get(f"/api/research/{research_id}/report")
        assert report_response.status_code == 200
        report = report_response.json()
        assert report["id"] == project["report_id"]
        assert report["research_id"] == research_id
        assert report["sources"] and report["facilities"] and report["claims"]
        assert report["conflicts"], "The explicit contradictory fixture must not be hidden."
        source_ids = {source["id"] for source in report["sources"]}
        source_urls = {source["url"] for source in report["sources"]}
        assert all(claim["source_id"] in source_ids for claim in report["claims"])
        assert all(claim["source_url"] in source_urls for claim in report["claims"])
        assert {claim["is_verified"] for claim in report["claims"]} == {False}
        assert all(claim["claim_a"]["source_url"] != claim["claim_b"]["source_url"] for claim in report["conflicts"])
        assert all(claim["claim_a"]["source_url"] in source_urls and claim["claim_b"]["source_url"] in source_urls
                   for claim in report["conflicts"])

        geo_response = client.get(f"/api/research/{research_id}/geographic-analysis")
        assert geo_response.status_code == 200
        assert geo_response.json()["radius_km"] == 10
        assert client.get(f"/api/research/{research_id}").json()["research_id"] == research_id

    assert db.get_by_id("research_projects", research_id)["status"] == "completed"
    assert len(db.select("research_tasks", {"research_project_id": research_id})) == 2
    persisted_sources = db.select("sources")
    assert len(persisted_sources) == 2
    assert all(item["extraction_status"] == "success" and item["extracted_text"] for item in persisted_sources)
    persisted_report = db.get_by_id("research_reports", project["report_id"])
    assert persisted_report["content"]["research_id"] == research_id

