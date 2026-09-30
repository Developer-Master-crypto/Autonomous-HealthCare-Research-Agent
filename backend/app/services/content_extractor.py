"""HTML content extraction and source extraction-status persistence."""

from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import List, Optional, Set

from starlette.concurrency import run_in_threadpool

from backend.app.models.db_models import SourceModel
from backend.app.repositories.source_repository import SourceRepository
from backend.app.services.source_fetcher import FetchStatus, SourceFetcher


class _ReadableTextParser(HTMLParser):
    """Collect title and visible text while excluding common page chrome."""

    ignored_tags: Set[str] = {"script", "style", "nav", "footer", "header", "aside", "form", "svg", "noscript", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._in_title = False
        self._title_parts: List[str] = []
        self._text_parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self.ignored_tags:
            self._ignored_depth += 1
        if tag == "title" and not self._ignored_depth:
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag in self.ignored_tags and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        if self._in_title:
            self._title_parts.append(text)
        elif not self._ignored_depth:
            self._text_parts.append(text)

    @property
    def title(self) -> Optional[str]:
        value = " ".join(self._title_parts).strip()
        return value or None

    @property
    def text(self) -> str:
        return " ".join(self._text_parts).strip()


class ContentExtractor:
    """Fetch, clean, truncate, and persist content for selected research sources."""

    def __init__(self, fetcher: SourceFetcher, source_repository: SourceRepository, max_content_chars: int = 12000) -> None:
        if max_content_chars < 1:
            raise ValueError("max_content_chars must be at least 1")
        self.fetcher = fetcher
        self.source_repository = source_repository
        self.max_content_chars = max_content_chars

    async def extract_and_store(self, source: SourceModel) -> SourceModel:
        """Extract actual source content or record why analysis was not possible."""
        result = await self.fetcher.fetch(source.url)
        extracted_at = datetime.now(timezone.utc)
        if result.status != FetchStatus.SUCCESS:
            return await run_in_threadpool(self._persist, source, {
                "extraction_status": result.status.value,
                "extraction_error": result.error,
                "extracted_text": None,
                "extracted_at": extracted_at,
            })
        try:
            parser = _ReadableTextParser()
            parser.feed(result.content or "")
            parser.close()
            extracted_text = parser.text[:self.max_content_chars]
        except Exception:
            return await run_in_threadpool(self._persist, source, {
                "extraction_status": "malformed_html",
                "extraction_error": "The source HTML could not be parsed.",
                "extracted_text": None,
                "extracted_at": extracted_at,
            })
        if not extracted_text:
            return await run_in_threadpool(self._persist, source, {
                "extraction_status": "no_extractable_content",
                "extraction_error": "The page did not contain extractable text.",
                "extracted_text": None,
                "extracted_at": extracted_at,
            })
        updates = {
            "url": result.final_url,
            "extraction_status": FetchStatus.SUCCESS.value,
            "extraction_error": None,
            "extracted_text": extracted_text,
            "extracted_at": extracted_at,
        }
        if parser.title:
            updates["title"] = parser.title
        return await run_in_threadpool(self._persist, source, updates)

    def _persist(self, source: SourceModel, updates: dict) -> SourceModel:
        """Persist status even when fetching failed; create sources supplied outside discovery."""
        existing = self.source_repository.get_by_id(source.id)
        if existing is None:
            source = self.source_repository.create(source)
        updated = self.source_repository.update(source.id, updates)
        if updated is None:
            raise RuntimeError("Failed to persist source extraction status.")
        return updated
