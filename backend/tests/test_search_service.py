"""Tests for multi-source research search using no network or credentials."""

import pytest

from backend.app.db.connection import MockDatabaseClient
from backend.app.repositories.source_repository import SourceRepository
from backend.app.schemas.research import ResearchTask
from backend.app.services.search_provider import MockSearchProvider, SearchProviderError
from backend.app.services.search_service import SearchService, SearchServiceError


def task():
    return ResearchTask(research_id="project-1", title="Discover facilities", description="Find cardiac services in Whitefield")


@pytest.mark.asyncio
async def test_successful_search_normalizes_and_persists_results():
    repository = SourceRepository(MockDatabaseClient())
    provider = MockSearchProvider([{"title": "Health registry", "url": "https://health.gov/cardiac", "content": "Registry entry"}])

    results = await SearchService(provider, repository, backoff_seconds=0).search_task(task())

    assert results[0].domain == "health.gov"
    assert results[0].snippet == "Registry entry"
    assert results[0].source_type.value == "government_registry"
    assert repository.get_by_url("https://health.gov/cardiac") is not None


@pytest.mark.asyncio
async def test_empty_results_are_returned_without_fabrication():
    results = await SearchService(MockSearchProvider(), SourceRepository(MockDatabaseClient())).search_task(task())
    assert results == []


@pytest.mark.asyncio
async def test_duplicate_and_invalid_urls_are_excluded():
    provider = MockSearchProvider([
        {"title": "One", "url": "https://example.org/a", "content": "A"},
        {"title": "Duplicate", "url": "https://example.org/a/", "content": "B"},
        {"title": "Bad", "url": "not-a-url", "content": "C"},
    ])

    results = await SearchService(provider, SourceRepository(MockDatabaseClient())).search_task(task())
    assert [result.url for result in results] == ["https://example.org/a"]


@pytest.mark.asyncio
async def test_retryable_api_failure_is_retried_then_reported():
    provider = MockSearchProvider(error=SearchProviderError("rate limited", retryable=True))

    with pytest.raises(SearchServiceError, match="provider failure"):
        await SearchService(provider, SourceRepository(MockDatabaseClient()), backoff_seconds=0).search_task(task())
    assert provider.calls == 3


@pytest.mark.asyncio
async def test_timeout_is_retried_then_reported():
    provider = MockSearchProvider(error=SearchProviderError("timed out", retryable=True))

    with pytest.raises(SearchServiceError):
        await SearchService(provider, SourceRepository(MockDatabaseClient()), max_attempts=2, backoff_seconds=0).search_task(task())
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_malformed_results_are_rejected():
    provider = MockSearchProvider([None, "not an object", {"title": "No URL"}, {"url": "https://example.org/no-title"}])

    results = await SearchService(provider, SourceRepository(MockDatabaseClient())).search_task(task())
    assert results == []
