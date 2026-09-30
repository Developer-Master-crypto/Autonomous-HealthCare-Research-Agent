"""Central API router registry aggregating all API endpoints."""

from fastapi import APIRouter
from backend.app.api.health import router as health_router
from backend.app.api.research import router as research_router
from backend.app.api.sources import router as sources_router
from backend.app.api.facilities import router as facilities_router
from backend.app.api.analysis import router as analysis_router
from backend.app.api.reports import router as reports_router

api_router = APIRouter(prefix="/api")

# Register all domain routers under /api
api_router.include_router(health_router)
api_router.include_router(research_router)
api_router.include_router(sources_router)
api_router.include_router(facilities_router)
api_router.include_router(analysis_router)
api_router.include_router(reports_router)
