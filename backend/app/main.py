"""FastAPI application factory and main server entry point."""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.core.exceptions import register_exception_handlers
from backend.app.api.router import api_router
from backend.app.utils.logger import logger


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Autonomous Healthcare Infrastructure Research Agent API - Team Spideyx (GATEWAYS 2026)",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Configure CORS middleware for local frontend development and external consumers
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register centralized exception handlers for standard JSON error envelopes
    register_exception_handlers(app)

    # Register all API endpoints under /api
    app.include_router(api_router)

    # Mount the frontend directory if it exists, providing zero-config local UI access
    frontend_path = Path(__file__).resolve().parent.parent.parent / "frontend"
    if frontend_path.exists():
        app.mount("/ui", StaticFiles(directory=str(frontend_path), html=True), name="frontend-ui")

    @app.get("/", summary="Root Welcome & Index")
    async def root_index() -> JSONResponse:
        """Root API metadata and quick link directory."""
        return JSONResponse(
            content={
                "project": "ResearchOps",
                "team": "Spideyx",
                "hackathon": "GATEWAYS 2026",
                "version": settings.VERSION,
                "endpoints": {
                    "health": "/api/health",
                    "research": "/api/research",
                    "sources": "/api/sources",
                    "facilities": "/api/facilities",
                    "analysis": "/api/analysis",
                    "reports": "/api/reports",
                    "docs": "/docs",
                    "ui": "/ui/",
                },
            }
        )

    logger.info(f"{settings.PROJECT_NAME} v{settings.VERSION} initialized successfully in {settings.ENVIRONMENT} mode.")
    return app


app = create_app()
