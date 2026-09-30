"""Central API router registry aggregating all API endpoints."""

from fastapi import APIRouter
from backend.app.api.health import router as health_router

api_router = APIRouter(prefix="/api")

# Register health check router under /api/health
api_router.include_router(health_router)
