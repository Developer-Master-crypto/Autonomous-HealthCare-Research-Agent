"""Schemas for healthcare facilities and clinical service offerings."""

from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class FacilityType(str, Enum):
    """Categorization of healthcare facilities."""
    ACUTE_CARE_HOSPITAL = "acute_care_hospital"
    CRITICAL_ACCESS_HOSPITAL = "critical_access_hospital"
    CHILDRENS_HOSPITAL = "childrens_hospital"
    TRAUMA_CENTER = "trauma_center"
    AMBULATORY_CLINIC = "ambulatory_clinic"
    SPECIALTY_CENTER = "specialty_center"
    OTHER = "other"


class ServiceStatus(str, Enum):
    """Operational status of a specific medical service line."""
    OPERATIONAL = "operational"
    REDUCED_CAPACITY = "reduced_capacity"
    DISCONTINUED = "discontinued"
    PENDING_VERIFICATION = "pending_verification"
    UNKNOWN = "unknown"


class Service(BaseModel):
    """Specific clinical service line or specialty unit offered within a facility."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    facility_id: str
    name: str = Field(..., description="Service line name (e.g. 'Pediatric Oncology', 'Level 1 Trauma ED')")
    category: str = Field(..., description="High-level category (e.g. 'pediatrics', 'oncology', 'emergency')")
    status: ServiceStatus = Field(default=ServiceStatus.OPERATIONAL)
    capacity: Optional[int] = Field(default=None, description="Dedicated bed or patient capacity if known")
    notes: Optional[str] = Field(default=None, description="Operational notes or recent changes")


class Facility(BaseModel):
    """Healthcare infrastructure facility entity."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., description="Official facility or hospital name")
    facility_type: FacilityType = Field(default=FacilityType.ACUTE_CARE_HOSPITAL)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    total_beds: Optional[int] = Field(default=None, ge=0)
    icu_beds: Optional[int] = Field(default=None, ge=0)
    trauma_level: Optional[str] = Field(default=None, description="e.g., 'Level I', 'Level II', 'Level III', 'None'")
    metadata: Dict[str, Any] = Field(default_factory=dict)
