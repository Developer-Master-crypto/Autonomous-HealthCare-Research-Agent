"""Schemas for research query requests, decomposition tasks, and response sessions."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class ResearchStatus(str, Enum):
    """Lifecycle status of a research inquiry."""
    PENDING = "pending"
    DECOMPOSING = "decomposing"
    GATHERING = "gathering"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatus(str, Enum):
    """Status of an individual decomposed sub-task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchTask(BaseModel):
    """Discrete atomic task decomposed from an overarching research inquiry."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    research_id: str
    title: str = Field(..., description="Concise task title")
    description: str = Field(..., description="Actionable scope and objective of the task")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    order: int = Field(default=1, description="Execution sequence index")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResearchRequest(BaseModel):
    """Inbound natural language healthcare research request."""

    query: str = Field(
        ...,
        min_length=5,
        description="Natural language question regarding healthcare infrastructure, capacity, or services",
        examples=["Assess pediatric oncology bed shortages and travel disparities in southeastern Ohio."],
    )
    region: Optional[str] = Field(
        default=None,
        description="Target geographic boundary (state, county, zip code, or metropolitan area)",
        examples=["Southeastern Ohio"],
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional execution constraints (e.g., maximum search depth, focus services)",
    )


class ResearchResponse(BaseModel):
    """Stateful research session representation."""

    research_id: str = Field(default_factory=lambda: str(uuid4()))
    query: str
    region: Optional[str] = None
    status: ResearchStatus = Field(default=ResearchStatus.PENDING)
    tasks: List[ResearchTask] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
