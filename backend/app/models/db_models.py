"""Domain database models representing the 12 Supabase/PostgreSQL tables."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ResearchProjectModel(BaseModel):
    """Model for research_projects table."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_query: str
    status: str = "pending"
    region: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResearchTaskModel(BaseModel):
    """Model for research_tasks table."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    research_project_id: str
    task_type: str
    description: str
    status: str = "pending"
    priority: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SourceModel(BaseModel):
    """Model for sources table."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    research_project_id: Optional[str] = None
    url: str
    title: str
    domain: Optional[str] = None
    source_type: str = "other"
    snippet: Optional[str] = None
    publisher: Optional[str] = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reliability_score: Optional[float] = None
    extracted_text: Optional[str] = None
    extraction_status: str = "pending"
    extraction_error: Optional[str] = None
    extracted_at: Optional[datetime] = None


class FacilityModel(BaseModel):
    """Model for facilities table."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    research_project_id: Optional[str] = None
    name: str
    facility_type: str = "acute_care_hospital"
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    trauma_level: Optional[str] = None
    total_beds: Optional[int] = None
    icu_beds: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ServiceModel(BaseModel):
    """Model for services table."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FacilityServiceModel(BaseModel):
    """Model for facility_services association table."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    facility_id: str
    service_id: str
    evidence_source_id: Optional[str] = None
    status: str = "operational"
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResearchClaimModel(BaseModel):
    """Model for research_claims table."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    research_project_id: str
    claim_text: str
    status: str = "unverified"
    confidence: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClaimEvidenceModel(BaseModel):
    """Model for claim_evidence table."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    claim_id: str
    source_id: str
    evidence_text: str
    confidence: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConflictModel(BaseModel):
    """Model for conflicts table."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    research_project_id: str
    topic: str
    description: str
    source_ids: List[str] = Field(default_factory=list)
    claim_a_id: Optional[str] = None
    claim_b_id: Optional[str] = None
    status: str = "unresolved"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GeographicObservationModel(BaseModel):
    """Model for geographic_observations table."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    research_project_id: str
    area: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    observation_type: str = "proximity_cluster"
    observation_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ServiceGapModel(BaseModel):
    """Model for service_gaps table."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    research_project_id: str
    area: str
    service: str
    evidence: Optional[str] = None
    confidence: Optional[float] = None
    severity: str = "medium"
    status: Optional[str] = None
    summary: Optional[str] = None
    limitations: List[str] = Field(default_factory=list)
    nearest_facility_distance_km: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResearchReportModel(BaseModel):
    """Model for research_reports table."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    research_project_id: str
    title: str
    content: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
