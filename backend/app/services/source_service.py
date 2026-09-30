"""Source registry and evidence attribution service."""

from typing import Dict, List, Optional

from backend.app.schemas.source import ResearchSource, SourceType
from backend.app.utils.logger import logger


class SourceService:
    """Manages discovery, provenance tracking, and retrieval of external evidence sources."""

    def __init__(self) -> None:
        # In-memory registry cache; will synchronize with Supabase in future milestones
        self._sources: Dict[str, ResearchSource] = {}

    def register_source(
        self,
        url: str,
        title: str,
        source_type: SourceType = SourceType.OTHER,
        publisher: Optional[str] = None,
        reliability_score: Optional[float] = None,
    ) -> ResearchSource:
        """Register and store an evidence source with metadata and canonical attribution URL."""
        source = ResearchSource(
            url=url,
            title=title,
            source_type=source_type,
            publisher=publisher,
            reliability_score=reliability_score,
        )
        self._sources[source.id] = source
        logger.info(f"Registered evidence source [{source.id}].")
        return source

    def get_source(self, source_id: str) -> Optional[ResearchSource]:
        """Retrieve an evidence source by unique identifier."""
        return self._sources.get(source_id)

    def list_sources(self) -> List[ResearchSource]:
        """List all currently registered evidence sources."""
        return list(self._sources.values())
