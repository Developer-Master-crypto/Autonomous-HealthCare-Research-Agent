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


def safe_fetcher(handler, **kwargs):
    return SourceFetcher(http_client=client_for(handler), resolver=lambda host: ["93.184.216.34"], **kwargs)


@pytest.mark.asyncio
async def test_extracts_content_removes_navigation_and_persists_metadata():
    async def handler(request):
        return httpx.Response(200, headers={"content-type": "text/html"}, text="""
            <html><title>Cardiac Care</title><nav>Menu links</nav><body><main>Useful cardiac service information.</main><footer>Footer</footer></body></html>
        """)

    repository = SourceRepository(MockDatabaseClient())
    extractor = ContentExtractor(safe_fetcher(handler), repository, max_content_chars=30)
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
    extractor = ContentExtractor(safe_fetcher(handler), repository)
    stored = await extractor.extract_and_store(SourceModel(url="https://example.org/start", title="Start", domain="example.org"))
    assert stored.url == "https://example.org/final"


@pytest.mark.asyncio
async def test_http_errors_and_restricted_pages_are_not_marked_analyzed():
    async def handler(request):
        return httpx.Response(403, request=request)

    repository = SourceRepository(MockDatabaseClient())
    extractor = ContentExtractor(safe_fetcher(handler), repository)
    stored = await extractor.extract_and_store(SourceModel(url="https://blocked.example/page", title="Blocked", domain="blocked.example"))
    assert stored.extraction_status == "restricted"
    assert stored.extracted_text is None


@pytest.mark.asyncio
async def test_timeout_is_recorded_without_content():
    async def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    repository = SourceRepository(MockDatabaseClient())
    extractor = ContentExtractor(safe_fetcher(handler), repository)
    stored = await extractor.extract_and_store(SourceModel(url="https://slow.example/page", title="Slow", domain="slow.example"))
    assert stored.extraction_status == "timeout"
    assert stored.extracted_text is None


@pytest.mark.asyncio
async def test_malformed_or_non_html_results_are_handled_without_fabrication():
    async def handler(request):
        return httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"not html")

    repository = SourceRepository(MockDatabaseClient())
    extractor = ContentExtractor(safe_fetcher(handler), repository)
    stored = await extractor.extract_and_store(SourceModel(url="https://example.org/file.pdf", title="PDF", domain="example.org"))
    assert stored.extraction_status == FetchStatus.UNSUPPORTED_CONTENT.value
    assert stored.extracted_text is None


@pytest.mark.asyncio
async def test_private_ip_urls_are_rejected_before_request():
    requested = []
    async def handler(request):
        requested.append(str(request.url))
        return httpx.Response(200, request=request, text="secret")
    fetcher = safe_fetcher(handler)
    result = await fetcher.fetch("http://127.0.0.1/admin")
    assert result.status == FetchStatus.INVALID_URL
    assert requested == []


@pytest.mark.asyncio
async def test_public_url_redirect_to_private_ip_is_blocked():
    requested = []
    async def handler(request):
        requested.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data/"}, request=request)
    result = await safe_fetcher(handler).fetch("https://example.org/start")
    assert result.status == FetchStatus.INVALID_URL
    assert len(requested) == 1


@pytest.mark.asyncio
async def test_credentials_and_nonstandard_ports_are_rejected():
    fetcher = SourceFetcher()
    assert (await fetcher.fetch("https://user:pass@example.org/" )).status == FetchStatus.INVALID_URL
    assert (await fetcher.fetch("http://example.org:8080/" )).status == FetchStatus.INVALID_URL


@pytest.mark.asyncio
async def test_source_response_size_is_bounded():
    async def handler(request):
        return httpx.Response(200, headers={"content-type": "text/html"}, content=b"x" * 32, request=request)
    result = await safe_fetcher(handler, max_bytes=16).fetch("https://example.org/large")
    assert result.status == FetchStatus.UNSUPPORTED_CONTENT
    assert result.content is None


@pytest.mark.asyncio
async def test_malformed_url_is_rejected_without_crashing():
    result = await SourceFetcher().fetch("http://[invalid")
    assert result.status == FetchStatus.INVALID_URL
