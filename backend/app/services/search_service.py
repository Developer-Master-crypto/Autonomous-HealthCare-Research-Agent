"""Multi-source research search with validation, retries, and source persistence."""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.parse import urlparse

from backend.app.core.config import settings
from backend.app.models.db_models import SourceModel
from backend.app.repositories.source_repository import SourceRepository
from backend.app.schemas.research import ResearchTask
from backend.app.schemas.search import SearchResult
from backend.app.schemas.source import SourceType
from backend.app.services.search_provider import SearchProvider, SearchProviderError, TavilySearchProvider


class SearchServiceError(Exception):
    """Raised when a research search cannot complete safely."""


class SearchService:
    """Search research tasks and persist trustworthy normalized source metadata."""

    def __init__(
        self,
        provider: Optional[SearchProvider] = None,
        source_repository: Optional[SourceRepository] = None,
        max_attempts: int = 3,
        backoff_seconds: float = 0.25,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.provider = provider or TavilySearchProvider(
            api_key=settings.TAVILY_API_KEY,
            timeout_seconds=settings.SEARCH_TIMEOUT_SECONDS,
        )
        self.source_repository = source_repository or SourceRepository()
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds

    async def search_task(self, task: ResearchTask) -> List[SearchResult]:
        """Search using task scope, validate results, deduplicate, and store sources."""
        raw_results = await self._search_with_retries(task.description)
        normalized = self._normalize(raw_results)
        for result in normalized:
            if self.source_repository.get_by_url(result.url) is None:
                self.source_repository.create(
                    SourceModel(
                        url=result.url,
                        title=result.title,
                        domain=result.domain,
                        source_type=result.source_type.value,
                        snippet=result.snippet,
                        retrieved_at=result.retrieved_at,
                    )
                )
        return normalized

    async def _search_with_retries(self, query: str) -> List[Dict]:
        last_error: Optional[SearchProviderError] = None
        for attempt in range(self.max_attempts):
            try:
                return await self.provider.search(query, settings.SEARCH_MAX_RESULTS)
            except SearchProviderError as exc:
                last_error = exc
                if not exc.retryable or attempt == self.max_attempts - 1:
                    break
                await asyncio.sleep(self.backoff_seconds * (2 ** attempt))
        raise SearchServiceError("Search could not be completed due to a provider failure.") from last_error

    @staticmethod
    def _normalize(raw_results: List[Dict]) -> List[SearchResult]:
        normalized: List[SearchResult] = []
        seen_urls = set()
        for raw_result in raw_results:
            if not isinstance(raw_result, dict):
                continue
            url = raw_result.get("url")
            title = raw_result.get("title")
            if not isinstance(url, str) or not isinstance(title, str) or not title.strip():
                continue
            parsed_url = urlparse(url)
            if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
                continue
            canonical_url = url.rstrip("/")
            if canonical_url in seen_urls:
                continue
            seen_urls.add(canonical_url)
            domain = parsed_url.netloc.lower()
            source_type = SearchService._source_type(domain, raw_result.get("source_type"))
            normalized.append(
                SearchResult(
                    title=title.strip(),
                    url=url,
                    snippet=raw_result.get("content") or raw_result.get("snippet"),
                    domain=domain,
                    source_type=source_type,
                    retrieved_at=datetime.now(timezone.utc),
                )
            )
        return normalized

    @staticmethod
    def _source_type(domain: str, provided_type: object) -> SourceType:
        try:
            return SourceType(provided_type) if provided_type else SearchService._classify_domain(domain)
        except ValueError:
            return SearchService._classify_domain(domain)

    @staticmethod
    def _classify_domain(domain: str) -> SourceType:
        if domain.endswith(".gov"):
            return SourceType.GOVERNMENT_REGISTRY
        if "pubmed" in domain or "nih.gov" in domain:
            return SourceType.ACADEMIC_PUBLICATION
        return SourceType.OTHER
