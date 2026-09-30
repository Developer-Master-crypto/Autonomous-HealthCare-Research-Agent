"""Validated contracts for autonomous research task planning."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlannedResearchTask(BaseModel):
    """A single actionable, evidence-oriented research task."""

    model_config = ConfigDict(extra="forbid")

    task_type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    required_evidence: List[str] = Field(default_factory=list)


class ResearchPlan(BaseModel):
    """Structured extraction and work plan for a research request."""

    model_config = ConfigDict(extra="forbid")

    objective: str = Field(min_length=1)
    location: Optional[str] = None
    radius_km: Optional[float] = Field(default=None, gt=0)
    service: Optional[str] = None
    required_entities: List[str] = Field(default_factory=list)
    tasks: List[PlannedResearchTask] = Field(min_length=1)
    required_evidence: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)

    @field_validator("location", "service", mode="before")
    @classmethod
    def blank_values_are_missing(cls, value: Optional[str]) -> Optional[str]:
        if isinstance(value, str) and not value.strip():
            return None
        return value
