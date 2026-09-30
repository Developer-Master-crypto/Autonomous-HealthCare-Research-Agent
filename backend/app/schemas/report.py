"""Schemas for synthesized evidence-backed research reports."""

from datetime import datetime, timezone
from typing import List
from uuid import uuid4

from pydantic import BaseModel, Field

from backend.app.schemas.analysis import Conflict, ServiceGap
from backend.app.schemas.facility import Facility
from backend.app.schemas.source import ResearchClaim, ResearchSource


class ResearchReport(BaseModel):
    """Complete, evidence-backed healthcare infrastructure research dossier."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    research_id: str = Field(..., description="ID of the parent research query session")
    title: str = Field(..., description="Report title")
    query: str = Field(..., description="Original user research question")
    executive_summary: str = Field(..., description="High-level synthesized summary of findings")
    methodology_note: str = Field(
        default=(
            "Synthesized by ResearchOps autonomous decision-support agent. "
            "All claims are attributed to referenced sources. "
            "This application provides research intelligence and is not intended for medical diagnosis or treatment."
        ),
        description="Disclaimer and provenance notice",
    )
    claims: List[ResearchClaim] = Field(default_factory=list, description="Extracted factual claims")
    conflicts: List[Conflict] = Field(default_factory=list, description="Contradictions flagged across sources")
    service_gaps: List[ServiceGap] = Field(default_factory=list, description="Identified healthcare service deserts")
    facilities: List[Facility] = Field(default_factory=list, description="Cataloged facilities relevant to inquiry")
    sources: List[ResearchSource] = Field(default_factory=list, description="Complete bibliography of cited sources")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
