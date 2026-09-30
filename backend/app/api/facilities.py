"""Healthcare facilities API endpoints."""

from typing import List
from fastapi import APIRouter, HTTPException, status
from backend.app.schemas.facility import Facility
from backend.app.services import geographic_service

router = APIRouter(prefix="/facilities", tags=["Facilities"])


@router.get(
    "",
    response_model=List[Facility],
    status_code=status.HTTP_200_OK,
    summary="List Facilities",
    description="Lists cataloged healthcare facilities and clinical institutions.",
)
async def list_facilities() -> List[Facility]:
    """Retrieve cataloged healthcare facilities."""
    return geographic_service.list_facilities()


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Facility with ID '{facility_id}' was not found.",
        )
    return facility
