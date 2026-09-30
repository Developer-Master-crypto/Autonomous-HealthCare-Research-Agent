"""Research session API endpoints."""

from typing import List
from fastapi import APIRouter, HTTPException, status
from backend.app.schemas.research import ResearchRequest, ResearchResponse
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
