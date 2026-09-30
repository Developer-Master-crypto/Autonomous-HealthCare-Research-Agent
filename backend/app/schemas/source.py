"""Schemas for external research sources, citations, and extracted factual claims."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Categorical classification of external evidence sources."""
    GOVERNMENT_REGISTRY = "government_registry"      # CMS, CDC, State Depts of Health
    CLINICAL_REGISTRY = "clinical_registry"          # NPI, AHA, Trauma registries
    ACADEMIC_PUBLICATION = "academic_publication"    # PubMed, peer-reviewed literature
    VERIFIED_NEWS = "verified_news"                  # Local press, healthcare journalism
    OFFICIAL_HOSPITAL_PORTAL = "official_portal"     # Hospital annual reports, censuses
    OTHER = "other"


class ResearchSource(BaseModel):
    """External evidence artifact discovered and referenced during investigation."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    url: str = Field(..., description="Canonical URL of the source")
    title: str = Field(..., description="Document or page title")
    source_type: SourceType = Field(default=SourceType.OTHER)
    publisher: Optional[str] = Field(default=None, description="Authoring agency or organization")
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reliability_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Assessed trustworthiness score (0.0 - 1.0)",
    )


class ResearchClaim(BaseModel):
    """Discrete factual statement or metric attributed to a primary source."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    statement: str = Field(..., description="The factual assertion (e.g. 'Facility operates 32 pediatric beds')")
    source_id: Optional[str] = Field(default=None, description="Referenced ResearchSource ID")
    source_url: Optional[str] = Field(default=None, description="Direct URL where assertion is grounded")
    supporting_evidence: Optional[str] = Field(default=None, description="Verbatim source excerpt supporting or contradicting the claim")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Extraction confidence score")
    is_verified: bool = Field(default=False, description="Whether claim has been verified across independent sources")
    extraction_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
