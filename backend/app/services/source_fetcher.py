"""Safe HTTP fetching for external research sources."""

from dataclasses import dataclass
from enum import Enum
import asyncio
import ipaddress
import socket
from typing import Callable, Optional
from urllib.parse import urljoin, urlparse

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

    def __init__(self, timeout_seconds: float = 15.0, http_client: Optional[httpx.AsyncClient] = None,
                 resolver: Optional[Callable[[str], list[str]]] = None, max_bytes: int = 2_000_000,
                 max_redirects: int = 5) -> None:
        self.timeout_seconds = timeout_seconds
        self.http_client = http_client
        self.resolver = resolver or self._resolve
        self.max_bytes = max_bytes
        self.max_redirects = max_redirects

    async def fetch(self, url: str) -> FetchResult:
        """Fetch one source without raising transport exceptions to callers."""
        if not self._is_valid_url(url):
            return FetchResult(url, url, FetchStatus.INVALID_URL, error="Only public absolute HTTP(S) URLs are supported.")
        try:
            current_url = url
            async with (self._client() if self.http_client is None else _existing_client(self.http_client)) as client:
                for redirect_count in range(self.max_redirects + 1):
                    parsed = urlparse(current_url)
                    if not await self._is_public_host(parsed.hostname or ""):
                        return FetchResult(url, current_url, FetchStatus.INVALID_URL, error="Source host is not publicly routable.")
                    async with client.stream("GET", current_url, follow_redirects=False, timeout=self.timeout_seconds) as response:
                        if response.status_code in {301, 302, 303, 307, 308}:
                            location = response.headers.get("location")
                            if not location or redirect_count == self.max_redirects:
                                return FetchResult(url, current_url, FetchStatus.INVALID_URL, error="Source redirect limit exceeded or invalid.")
                            next_url = urljoin(current_url, location)
                            if not self._is_valid_url(next_url):
                                return FetchResult(url, next_url, FetchStatus.INVALID_URL, error="Source redirected to an unsupported URL.")
                            current_url = next_url
                            continue
                        return await self._result_from_response(url, current_url, response)
                return FetchResult(url, current_url, FetchStatus.INVALID_URL, error="Source redirect limit exceeded.")
        except httpx.TimeoutException:
            return FetchResult(url, url, FetchStatus.TIMEOUT, error="The source request timed out.")
        except httpx.RequestError:
            return FetchResult(url, url, FetchStatus.UNAVAILABLE, error="The source could not be reached.")
        except (httpx.InvalidURL, ValueError):
            return FetchResult(url, url, FetchStatus.INVALID_URL, error="The source URL is invalid.")

    async def _result_from_response(self, requested_url: str, final_url: str, response: httpx.Response) -> FetchResult:
        final_url = str(response.url)
        if response.status_code in {401, 403, 451}:
            return FetchResult(requested_url, final_url, FetchStatus.RESTRICTED, error="The source restricts automated access.")
        if response.status_code >= 400:
            return FetchResult(requested_url, final_url, FetchStatus.HTTP_ERROR, error=f"Source returned HTTP {response.status_code}.")
        content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
        if content_type and content_type not in {"text/html", "application/xhtml+xml"}:
            return FetchResult(requested_url, final_url, FetchStatus.UNSUPPORTED_CONTENT, content_type=content_type, error="Source is not an HTML page.")
        declared_size = response.headers.get("content-length")
        if declared_size and declared_size.isdigit() and int(declared_size) > self.max_bytes:
            return FetchResult(requested_url, final_url, FetchStatus.UNSUPPORTED_CONTENT, content_type=content_type, error="Source exceeded the content size limit.")
        chunks, size = [], 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > self.max_bytes:
                return FetchResult(requested_url, final_url, FetchStatus.UNSUPPORTED_CONTENT, content_type=content_type, error="Source exceeded the content size limit.")
            chunks.append(chunk)
        content = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
        return FetchResult(requested_url, final_url, FetchStatus.SUCCESS, content=content, content_type=content_type or None)

    def _client(self):
        return httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=False)

    async def _is_public_host(self, host: str) -> bool:
        if not host or host.lower() == "localhost" or host.lower().endswith((".localhost", ".local")):
            return False
        try:
            addresses = [str(ipaddress.ip_address(host))]
        except ValueError:
            try:
                addresses = await asyncio.to_thread(self.resolver, host)
            except (OSError, socket.gaierror):
                return False
        if not addresses:
            return False
        try:
            return all(ipaddress.ip_address(address).is_global for address in addresses)
        except ValueError:
            return False

    @staticmethod
    def _resolve(host: str) -> list[str]:
        return list({item[4][0] for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)})

    @staticmethod
    def _is_valid_url(url: object) -> bool:
        if not isinstance(url, str):
            return False
        try:
            parsed = urlparse(url)
        except ValueError:
            return False
        try:
            port = parsed.port
        except ValueError:
            return False
        expected_port = 80 if parsed.scheme == "http" else 443
        return (parsed.scheme in {"http", "https"} and bool(parsed.hostname)
                and parsed.username is None and parsed.password is None
                and port in {None, expected_port})


class _existing_client:
    """Async context adapter that leaves an injected HTTP client open."""
    def __init__(self, client):
        self.client = client
    async def __aenter__(self):
        return self.client
    async def __aexit__(self, *_):
        return None
