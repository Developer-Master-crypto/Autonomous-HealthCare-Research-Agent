"""Evidence sources API endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException, status
from starlette.concurrency import run_in_threadpool

from backend.app.schemas.source import ResearchSource
from backend.app.services import source_repository, source_service

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
    registered = {item.id: item for item in source_service.list_sources()}
    try:
        stored = await run_in_threadpool(source_repository.list_all)
        registered.update({item.id: ResearchSource(
            id=item.id, url=item.url, title=item.title, source_type=item.source_type,
            publisher=item.publisher, retrieved_at=item.retrieved_at,
            reliability_score=item.reliability_score,
        ) for item in stored})
    except Exception:
        pass
    return list(registered.values())


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
        try:
            stored = await run_in_threadpool(source_repository.get_by_id, source_id)
            if stored:
                source = ResearchSource(
                    id=stored.id, url=stored.url, title=stored.title, source_type=stored.source_type,
                    publisher=stored.publisher, retrieved_at=stored.retrieved_at,
                    reliability_score=stored.reliability_score,
                )
        except Exception:
            source = None
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence source with ID '{source_id}' was not found.",
        )
    return source
