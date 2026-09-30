"""Safe HTTP fetching for external research sources."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from urllib.parse import urlparse

import httpx


class FetchStatus(str, Enum):
    SUCCESS = "success"
    INVALID_URL = "invalid_url"
    HTTP_ERROR = "http_error"
    TIMEOUT = "timeout"
    RESTRICTED = "restricted"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED_CONTENT = "unsupported_content"


@dataclass(frozen=True)
class FetchResult:
    """Outcome of a fetch attempt, including only actual HTTP response data."""

    requested_url: str
    final_url: str
    status: FetchStatus
    content: Optional[str] = None
    content_type: Optional[str] = None
    error: Optional[str] = None


class SourceFetcher:
    """Fetch HTTP(S) documents with redirects and access failures represented safely."""

    def __init__(self, timeout_seconds: float = 15.0, http_client: Optional[httpx.AsyncClient] = None) -> None:
        self.timeout_seconds = timeout_seconds
        self.http_client = http_client

    async def fetch(self, url: str) -> FetchResult:
        """Fetch one source without raising transport exceptions to callers."""
        if not self._is_valid_url(url):
            return FetchResult(url, url, FetchStatus.INVALID_URL, error="Only absolute HTTP(S) URLs are supported.")
        try:
            if self.http_client is not None:
                response = await self.http_client.get(url, follow_redirects=True, timeout=self.timeout_seconds)
            else:
                async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
                    response = await client.get(url)
        except httpx.TimeoutException:
            return FetchResult(url, url, FetchStatus.TIMEOUT, error="The source request timed out.")
        except httpx.RequestError:
            return FetchResult(url, url, FetchStatus.UNAVAILABLE, error="The source could not be reached.")

        final_url = str(response.url)
        if response.status_code in {401, 403, 451}:
            return FetchResult(url, final_url, FetchStatus.RESTRICTED, error="The source restricts automated access.")
        if response.status_code >= 400:
            return FetchResult(url, final_url, FetchStatus.HTTP_ERROR, error=f"Source returned HTTP {response.status_code}.")
        content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
        if content_type and content_type not in {"text/html", "application/xhtml+xml"}:
            return FetchResult(url, final_url, FetchStatus.UNSUPPORTED_CONTENT, content_type=content_type, error="Source is not an HTML page.")
        return FetchResult(url, final_url, FetchStatus.SUCCESS, content=response.text, content_type=content_type or None)

    @staticmethod
    def _is_valid_url(url: object) -> bool:
        if not isinstance(url, str):
            return False
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
