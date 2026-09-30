"""Provider abstraction and Tavily implementation for external web search."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx


class SearchProviderError(Exception):
    """A search-provider failure that may be safe to retry."""

    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class SearchProvider(ABC):
    """Port for search APIs used by research services."""

    @abstractmethod
    async def search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Return raw provider results without adding or inventing data."""
        raise NotImplementedError


class TavilySearchProvider(SearchProvider):
    """Tavily API adapter using environment-supplied credentials."""

    endpoint = "https://api.tavily.com/search"

    def __init__(
        self,
        api_key: str,
        timeout_seconds: float = 15.0,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        if not api_key:
            raise ValueError("TAVILY_API_KEY must be configured to use Tavily search.")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.http_client = http_client

    async def search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        payload = {"api_key": self.api_key, "query": query, "max_results": max_results}
        try:
            if self.http_client is not None:
                response = await self.http_client.post(self.endpoint, json=payload, timeout=self.timeout_seconds)
            else:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(self.endpoint, json=payload)
        except httpx.TimeoutException as exc:
            raise SearchProviderError("Search provider timed out.", retryable=True) from exc
        except httpx.RequestError as exc:
            raise SearchProviderError("Search provider request failed.", retryable=True) from exc

        if response.status_code == 429:
            raise SearchProviderError("Search provider rate limit reached.", retryable=True)
        if response.status_code >= 500:
            raise SearchProviderError("Search provider is unavailable.", retryable=True)
        if response.status_code >= 400:
            raise SearchProviderError("Search provider rejected the request.")
        try:
            data = response.json()
        except ValueError as exc:
            raise SearchProviderError("Search provider returned malformed JSON.") from exc
        results = data.get("results")
        if not isinstance(results, list):
            raise SearchProviderError("Search provider response did not contain a results list.")
        return results


class MockSearchProvider(SearchProvider):
    """Deterministic search provider for tests without credentials or network access."""

    def __init__(self, results: Optional[List[Dict[str, Any]]] = None, error: Optional[Exception] = None) -> None:
        self.results = results or []
        self.error = error
        self.calls = 0

    async def search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        self.calls += 1
        if self.error:
            raise self.error
        return self.results[:max_results]
