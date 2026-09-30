"""Evidence-limited availability assessment contracts for healthcare services."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ServiceGapStatus(str, Enum):
    AVAILABILITY_DOCUMENTED = "availability_documented"
    COMPARATIVELY_LIMITED_AVAILABILITY = "comparatively_limited_availability"
    POTENTIAL_SERVICE_GAP = "potential_service_gap"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ServiceAvailabilityEvidence(BaseModel):
    """A source excerpt that explicitly confirms or disputes facility service availability."""

    facility_id: Optional[str] = None
    facility_name: str = Field(min_length=1)
    service: str = Field(min_length=1)
    evidence_text: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    availability_confirmed: bool = True


class ServiceGapAssessment(BaseModel):
    """Cautious, non-clinical assessment of documented service availability."""

    service: str
    geographic_area: str
    number_of_facilities_providing_service: int = Field(ge=0)
    supporting_facilities: List[str] = Field(default_factory=list)
    evidence: List[ServiceAvailabilityEvidence] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    status: ServiceGapStatus
    summary: str
