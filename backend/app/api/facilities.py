"""Healthcare facilities API endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException, status
from starlette.concurrency import run_in_threadpool

from backend.app.repositories.entity_repositories import FacilityRepository
from backend.app.schemas.facility import Facility
from backend.app.services import database_client, geographic_service

router = APIRouter(prefix="/facilities", tags=["Facilities"])
facility_repository = FacilityRepository(database_client)


@router.get(
    "",
    response_model=List[Facility],
    status_code=status.HTTP_200_OK,
    summary="List Facilities",
    description="Lists cataloged healthcare facilities and clinical institutions.",
)
async def list_facilities() -> List[Facility]:
    """Retrieve cataloged healthcare facilities."""
    facilities = {item.id: item for item in geographic_service.list_facilities()}
    try:
        facilities.update({item.id: Facility.model_validate(item.model_dump())
                           for item in await run_in_threadpool(facility_repository.list_all)})
    except Exception:
        pass
    return list(facilities.values())


@router.get(
    "/{facility_id}",
    response_model=Facility,
    status_code=status.HTTP_200_OK,
    summary="Get Facility",
    description="Retrieves a specific facility by its identifier.",
)
async def get_facility(facility_id: str) -> Facility:
    """Get facility by ID."""
    facility = geographic_service.get_facility(facility_id)
    if not facility:
        try:
            stored = await run_in_threadpool(facility_repository.get_by_id, facility_id)
            facility = Facility.model_validate(stored.model_dump()) if stored else None
        except Exception:
            facility = None
    if not facility:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Facility with ID '{facility_id}' was not found.",
        )
    return facility
