"""Contracts for normalized external search results."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from backend.app.schemas.source import SourceType


class SearchResult(BaseModel):
    """A validated search result returned by a provider-independent search service."""

    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    source_id: Optional[str] = None
    snippet: Optional[str] = None
    domain: str = Field(min_length=1)
    source_type: SourceType = SourceType.OTHER
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
