"""Health check endpoint handler."""

from fastapi import APIRouter, status
from starlette.concurrency import run_in_threadpool

from backend.app.schemas.health import HealthResponse
from backend.app.services import database_client

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


@router.get("/health/database", status_code=status.HTTP_200_OK, summary="Database connectivity check")
async def get_database_health() -> dict:
    """Return sanitized connectivity status for the configured database adapter."""
    try:
        return await run_in_threadpool(database_client.health_check)
    except Exception:
        return {"status": "unhealthy", "backend": "database"}
