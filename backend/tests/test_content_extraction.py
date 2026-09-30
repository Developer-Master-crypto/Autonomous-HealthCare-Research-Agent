"""Tests for safe source retrieval and HTML content extraction."""

import httpx
import pytest

from backend.app.db.connection import MockDatabaseClient
from backend.app.models.db_models import SourceModel
from backend.app.repositories.source_repository import SourceRepository
from backend.app.services.content_extractor import ContentExtractor
from backend.app.services.source_fetcher import FetchStatus, SourceFetcher


def client_for(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_extracts_content_removes_navigation_and_persists_metadata():
    async def handler(request):
        return httpx.Response(200, headers={"content-type": "text/html"}, text="""
            <html><title>Cardiac Care</title><nav>Menu links</nav><body><main>Useful cardiac service information.</main><footer>Footer</footer></body></html>
        """)

    repository = SourceRepository(MockDatabaseClient())
    extractor = ContentExtractor(SourceFetcher(http_client=client_for(handler)), repository, max_content_chars=30)
    stored = await extractor.extract_and_store(SourceModel(url="https://example.org/page", title="Search result", domain="example.org"))

    assert stored.title == "Cardiac Care"
    assert stored.extraction_status == "success"
    assert stored.extracted_text == "Useful cardiac service informa"
    assert "Menu links" not in stored.extracted_text


@pytest.mark.asyncio
async def test_redirects_preserve_the_actual_final_url():
    async def handler(request):
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "https://example.org/final"}, request=request)
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<p>Final page</p>")

    repository = SourceRepository(MockDatabaseClient())
    extractor = ContentExtractor(SourceFetcher(http_client=client_for(handler)), repository)
    stored = await extractor.extract_and_store(SourceModel(url="https://example.org/start", title="Start", domain="example.org"))
    assert stored.url == "https://example.org/final"


@pytest.mark.asyncio
async def test_http_errors_and_restricted_pages_are_not_marked_analyzed():
    async def handler(request):
        return httpx.Response(403, request=request)

    repository = SourceRepository(MockDatabaseClient())
    extractor = ContentExtractor(SourceFetcher(http_client=client_for(handler)), repository)
    stored = await extractor.extract_and_store(SourceModel(url="https://blocked.example/page", title="Blocked", domain="blocked.example"))
    assert stored.extraction_status == "restricted"
    assert stored.extracted_text is None


@pytest.mark.asyncio
async def test_timeout_is_recorded_without_content():
    async def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    repository = SourceRepository(MockDatabaseClient())
    extractor = ContentExtractor(SourceFetcher(http_client=client_for(handler)), repository)
    stored = await extractor.extract_and_store(SourceModel(url="https://slow.example/page", title="Slow", domain="slow.example"))
    assert stored.extraction_status == "timeout"
    assert stored.extracted_text is None


@pytest.mark.asyncio
async def test_malformed_or_non_html_results_are_handled_without_fabrication():
    async def handler(request):
        return httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"not html")

    repository = SourceRepository(MockDatabaseClient())
    extractor = ContentExtractor(SourceFetcher(http_client=client_for(handler)), repository)
    stored = await extractor.extract_and_store(SourceModel(url="https://example.org/file.pdf", title="PDF", domain="example.org"))
    assert stored.extraction_status == FetchStatus.UNSUPPORTED_CONTENT.value
    assert stored.extracted_text is None
