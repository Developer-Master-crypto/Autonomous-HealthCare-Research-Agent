"""Evidence-backed contracts for facility extraction from source content."""

from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class SourceEvidence(BaseModel):
    """Verbatim source evidence supporting an extracted entity or service."""

    supporting_text: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    source_title: str = Field(min_length=1)


class ExtractedHealthcareService(BaseModel):
    """A healthcare offering whose fields are grounded in source evidence."""

    specialty: Optional[str] = None
    department: Optional[str] = None
    healthcare_service: Optional[str] = None
    availability_confirmed: bool = True
    evidence: SourceEvidence

    @model_validator(mode="after")
    def require_a_service_value(self) -> "ExtractedHealthcareService":
        if not any((self.specialty, self.department, self.healthcare_service)):
            raise ValueError("An extracted service must contain a supported service value.")
        return self


class ExtractedFacility(BaseModel):
    """Facility details explicitly supported by a retrieved source."""

    name: str = Field(min_length=1)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    website: Optional[str] = None
    phone: Optional[str] = None
    evidence: SourceEvidence
    services: List[ExtractedHealthcareService] = Field(default_factory=list)


class FacilityExtractionResult(BaseModel):
    """All facility entities that can be supported by one source document."""

    source_url: str
    source_title: str
    facilities: List[ExtractedFacility] = Field(default_factory=list)
