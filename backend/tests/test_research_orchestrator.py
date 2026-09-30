"""Integration coverage for the bounded ResearchOps orchestration pipeline."""

import pytest

from backend.app.schemas.research import ResearchRequest, ResearchStatus
from backend.app.schemas.search import SearchResult
from backend.app.services.research_orchestrator import ResearchOrchestrator


class FakeSearchService:
    async def search_task(self, task):
        return [SearchResult(title="Hospital directory", url="https://example.org/directory", domain="example.org")]


@pytest.mark.asyncio
async def test_orchestrator_completes_a_bounded_run_and_reuses_sources():
    orchestrator = ResearchOrchestrator(search_service=FakeSearchService(), max_tasks=3)
    result = await orchestrator.run(ResearchRequest(query="Assess cardiology services in Whitefield", region="Whitefield"))
    assert result.status == ResearchStatus.COMPLETED
    assert result.progress.tasks_completed == 3
    assert result.progress.sources_retrieved == 1
    assert result.progress.sources_reused == 2
    assert result.report_id is not None


@pytest.mark.asyncio
async def test_orchestrator_records_missing_information_without_search_configuration():
    result = await ResearchOrchestrator(max_tasks=2).run(
        ResearchRequest(query="Assess trauma services in rural areas", region="Unknown Region")
    )
    assert result.status == ResearchStatus.COMPLETED
    assert result.execution_mode == "unconfigured"
    assert "SEARCH" in result.progress.skipped_stages
    assert "SEARCH" not in result.progress.completed_stages
    assert any("Search is not configured" in item for item in result.missing_information)
    assert result.report_id is not None


def test_research_status_endpoint_returns_structured_progress(client):
    response = client.post("/api/research", json={"query": "Assess cardiology access in Whitefield", "region": "Whitefield"})
    assert response.status_code == 201
    research_id = response.json()["research_id"]
    status_response = client.get(f"/api/research/{research_id}/status")
    assert status_response.status_code == 200
    assert status_response.json()["progress"]["current_stage"] == "COMPLETED"

    geographic_response = client.get(f"/api/research/{research_id}/geographic-analysis")
    assert geographic_response.status_code == 200
    assert geographic_response.json()["target"]["location"] == "Whitefield"
