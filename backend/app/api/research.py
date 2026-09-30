"""Research session API endpoints."""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status
from backend.app.schemas.research import ResearchRequest, ResearchResponse
from backend.app.schemas.report import ResearchReport
from backend.app.services import research_orchestrator

router = APIRouter(prefix="/research", tags=["Research"])


@router.post(
    "",
    response_model=ResearchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Research Session",
    description="Initiates a new research inquiry session and generates the preliminary task plan.",
)
async def create_research(request: ResearchRequest) -> ResearchResponse:
    """Create and execute a bounded evidence-first research project."""
    return await research_orchestrator.run(request)


@router.get(
    "",
    response_model=List[ResearchResponse],
    status_code=status.HTTP_200_OK,
    summary="List Research Sessions",
    description="Lists all initiated research inquiries.",
)
async def list_researches() -> List[ResearchResponse]:
    """Retrieve all research sessions."""
    return research_orchestrator.list_projects()


@router.get(
    "/{research_id}",
    response_model=ResearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Research Session",
    description="Retrieves a specific research inquiry session by its unique identifier.",
)
async def get_research(research_id: str) -> ResearchResponse:
    """Get research session by ID."""
    session = research_orchestrator.get_project(research_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research session with ID '{research_id}' was not found.",
        )
    return session


@router.get(
    "/{research_id}/status",
    response_model=ResearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Research Progress",
)
async def get_research_status(research_id: str) -> ResearchResponse:
    """Retrieve structured orchestration progress for a research project."""
    session = research_orchestrator.get_project(research_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Research session with ID '{research_id}' was not found.")
    return session


@router.get(
    "/{research_id}/geographic-analysis",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Geographic Analysis",
)
async def get_geographic_analysis(research_id: str) -> Dict[str, Any]:
    """Return stored geographic results without inventing missing coordinates."""
    session = research_orchestrator.get_project(research_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Research session with ID '{research_id}' was not found.")
    analysis = session.intermediate_results.get("geographic_analysis")
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Geographic analysis is unavailable for this research project.")
    return analysis


@router.get(
    "/{research_id}/report",
    response_model=ResearchReport,
    status_code=status.HTTP_200_OK,
    summary="Get Evidence-Backed Research Report",
)
async def get_research_report(research_id: str) -> ResearchReport:
    """Return the report generated for this research session."""
    session = research_orchestrator.get_project(research_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Research session with ID '{research_id}' was not found.")
    report = research_orchestrator.report_service.get_report_by_research_id(research_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research report is unavailable for this project.")
    return report
