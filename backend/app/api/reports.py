"""Research report API endpoints."""

from typing import List
from fastapi import APIRouter, HTTPException, status
from backend.app.schemas.report import ResearchReport
from backend.app.services import report_service

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get(
    "",
    response_model=List[ResearchReport],
    status_code=status.HTTP_200_OK,
    summary="List Research Reports",
    description="Lists all synthesized healthcare infrastructure research reports.",
)
async def list_reports() -> List[ResearchReport]:
    """Retrieve all synthesized reports."""
    return report_service.list_reports()


@router.get(
    "/{report_id}",
    response_model=ResearchReport,
    status_code=status.HTTP_200_OK,
    summary="Get Research Report",
    description="Retrieves a specific evidence dossier by its report identifier.",
)
async def get_report(report_id: str) -> ResearchReport:
    """Get report by ID."""
    report = report_service.get_report(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research report with ID '{report_id}' was not found.",
        )
    return report
