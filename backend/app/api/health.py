"""Health check endpoint handler."""

from fastapi import APIRouter, status
from backend.app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Returns current service status and service identifier.",
)
async def get_health() -> HealthResponse:
    """Perform a lightweight service health check."""
    return HealthResponse(
        status="ok",
        service="researchops-api",
    )
