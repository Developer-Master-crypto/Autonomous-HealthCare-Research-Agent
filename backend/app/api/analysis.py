"""Analysis API endpoints for conflict verification and service-gap assessments."""

from typing import List

from fastapi import APIRouter, status
from pydantic import BaseModel

from backend.app.schemas.analysis import Conflict, ServiceGap
from backend.app.services import gap_analysis_service, verification_service

router = APIRouter(prefix="/analysis", tags=["Analysis"])


class AnalysisOverview(BaseModel):
    """Aggregated analysis overview."""
    total_conflicts: int
    total_service_gaps: int
    conflicts: List[Conflict]
    service_gaps: List[ServiceGap]


@router.get(
    "",
    response_model=AnalysisOverview,
    status_code=status.HTTP_200_OK,
    summary="Get Analysis Overview",
    description="Returns an aggregated summary of identified evidentiary conflicts and healthcare service gaps.",
)
async def get_analysis_overview() -> AnalysisOverview:
    """Retrieve combined analysis results."""
    conflicts = verification_service.list_conflicts()
    gaps = gap_analysis_service.list_service_gaps()
    return AnalysisOverview(
        total_conflicts=len(conflicts),
        total_service_gaps=len(gaps),
        conflicts=conflicts,
        service_gaps=gaps,
    )


@router.get(
    "/conflicts",
    response_model=List[Conflict],
    status_code=status.HTTP_200_OK,
    summary="List Conflicts",
    description="Lists all detected evidentiary contradictions across independent healthcare data sources.",
)
async def list_conflicts() -> List[Conflict]:
    """Retrieve all flagged evidentiary conflicts."""
    return verification_service.list_conflicts()


@router.get(
    "/gaps",
    response_model=List[ServiceGap],
    status_code=status.HTTP_200_OK,
    summary="List Service Gaps",
    description="Lists identified regional service deficits and healthcare deserts.",
)
async def list_service_gaps() -> List[ServiceGap]:
    """Retrieve all recorded service gaps."""
    return gap_analysis_service.list_service_gaps()
