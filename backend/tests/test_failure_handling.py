"""Failure-mode regression tests: state is retained and provider details stay private."""

import pytest

from backend.app.schemas.research import ResearchRequest, ResearchStatus
from backend.app.services.research_orchestrator import ResearchOrchestrator


class FailingSearch:
    async def search_task(self, task):
        raise RuntimeError("token=super-secret provider outage")


class FailingReport:
    def generate_report(self, **kwargs):
        raise RuntimeError("DATABASE_URL=secret")


@pytest.mark.asyncio
async def test_search_failure_is_recorded_without_secret_or_fake_results():
    result = await ResearchOrchestrator(search_service=FailingSearch(), max_tasks=1).run(
        ResearchRequest(query="Assess access to emergency care", region="Unknown Region")
    )
    assert result.status == ResearchStatus.COMPLETED
    assert result.intermediate_results["source_count"] == 0
    assert "super-secret" not in " ".join(result.missing_information)
    assert any("Search failed" in item for item in result.missing_information)


@pytest.mark.asyncio
async def test_report_failure_preserves_project_without_secret():
    result = await ResearchOrchestrator(report_service=FailingReport(), max_tasks=1).run(
        ResearchRequest(query="Assess access to emergency care")
    )
    assert result.status == ResearchStatus.FAILED
    assert result.research_id
    assert "secret" not in (result.error or "").lower()


def test_empty_and_excessively_long_queries_are_rejected(client):
    assert client.post("/api/research", json={"query": ""}).status_code == 422
    assert client.post("/api/research", json={"query": "x" * 10001}).status_code == 422
