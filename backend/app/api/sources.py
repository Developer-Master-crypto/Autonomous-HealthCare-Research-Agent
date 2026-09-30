"""Evidence sources API endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException, status

from backend.app.schemas.source import ResearchSource
from backend.app.services import source_service

router = APIRouter(prefix="/sources", tags=["Sources"])


@router.get(
    "",
    response_model=List[ResearchSource],
    status_code=status.HTTP_200_OK,
    summary="List Evidence Sources",
    description="Lists all registered and retrieved evidence sources across healthcare registries.",
)
async def list_sources() -> List[ResearchSource]:
    """Retrieve all recorded research sources."""
    return source_service.list_sources()


@router.get(
    "/{source_id}",
    response_model=ResearchSource,
    status_code=status.HTTP_200_OK,
    summary="Get Evidence Source",
    description="Retrieves a specific evidence source by its identifier.",
)
async def get_source(source_id: str) -> ResearchSource:
    """Get source by ID."""
    source = source_service.get_source(source_id)
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence source with ID '{source_id}' was not found.",
        )
    return source
