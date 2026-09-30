"""Schemas for conflict detection, contradiction analysis, and service-gap identification."""

from enum import Enum
from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field

from backend.app.schemas.source import ResearchClaim


class ConflictStatus(str, Enum):
    """Resolution status of conflicting evidentiary claims."""
    UNRESOLVED = "unresolved"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    DATA_UNAVAILABLE = "data_unavailable"


class GapSeverity(str, Enum):
    """Severity classification of identified healthcare infrastructure deficits."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Conflict(BaseModel):
    """Representation of contradictory or discrepant assertions across sources."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    topic: str = Field(..., description="Subject matter of conflict (e.g. 'St. Jude ICU Bed Count')")
    claim_a: ResearchClaim = Field(..., description="First assertion with source attribution")
    claim_b: ResearchClaim = Field(..., description="Contradicting assertion with source attribution")
    description: str = Field(..., description="Explanation of the discrepancy")
    resolution_status: ConflictStatus = Field(default=ConflictStatus.UNRESOLVED)
    reconciliation_notes: Optional[str] = Field(default=None, description="Resolution rationale or findings")


class ServiceGap(BaseModel):
    """Geographic or capacity deficit in healthcare accessibility."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    region: str = Field(..., description="Geographic area or county experiencing the deficit")
    service_category: str = Field(..., description="Underserved specialty (e.g., 'Pediatric Intensive Care')")
    severity: GapSeverity = Field(default=GapSeverity.MEDIUM)
    description: str = Field(..., description="Detailed explanation of the healthcare gap")
    affected_population_estimate: Optional[int] = Field(default=None, ge=0)
    nearest_facility_distance_km: Optional[float] = Field(default=None, ge=0.0)
    recommended_action: Optional[str] = Field(default=None, description="Policy or resource allocation suggestion")
