"""Research report API endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException, status
from starlette.concurrency import run_in_threadpool

from backend.app.repositories.entity_repositories import ResearchReportRepository
from backend.app.schemas.report import ResearchReport
from backend.app.services import database_client, report_service

router = APIRouter(prefix="/reports", tags=["Reports"])
report_repository = ResearchReportRepository(database_client)


@router.get(
    "",
    response_model=List[ResearchReport],
    status_code=status.HTTP_200_OK,
    summary="List Research Reports",
    description="Lists all synthesized healthcare infrastructure research reports.",
)
async def list_reports() -> List[ResearchReport]:
    """Retrieve all synthesized reports."""
    reports = {item.id: item for item in report_service.list_reports()}
    try:
        stored = await run_in_threadpool(report_repository.list_all)
        reports.update({item.id: ResearchReport.model_validate(item.content) for item in stored})
    except Exception:
        pass
    return list(reports.values())


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
        try:
            stored = await run_in_threadpool(report_repository.get_by_id, report_id)
            report = ResearchReport.model_validate(stored.content) if stored else None
        except Exception:
            report = None
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research report with ID '{report_id}' was not found.",
        )
    return report
