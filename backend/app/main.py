"""FastAPI application factory and main server entry point."""

from collections import deque
from pathlib import Path
import time
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
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type"],
    )

    requests_by_client = {}
    @app.middleware("http")
    async def security_controls(request, call_next):
        if request.url.path == "/api/research" and request.method == "POST":
            client_key = request.client.host if request.client else "unknown"
            now = time.monotonic()
            if client_key not in requests_by_client:
                if len(requests_by_client) >= 4096:
                    for key in [key for key, values in requests_by_client.items() if not values or now - values[-1] >= 60]:
                        requests_by_client.pop(key, None)
                if len(requests_by_client) >= 4096:
                    client_key = "overflow"
            requests = requests_by_client.setdefault(client_key, deque())
            while requests and now - requests[0] >= 60:
                requests.popleft()
            if len(requests) >= settings.RESEARCH_RATE_LIMIT_PER_MINUTE:
                return JSONResponse(status_code=429, content={"error": {"code": "RATE_LIMITED", "message": "Research request limit reached. Try again shortly."}}, headers={"Retry-After": "60"})
            requests.append(now)
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > 1_000_000:
            return JSONResponse(status_code=413, content={"error": {"code": "PAYLOAD_TOO_LARGE", "message": "Request payload exceeds the size limit."}})
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net https://unpkg.com; style-src 'self' https://unpkg.com 'unsafe-inline'; img-src 'self' data: https://*.tile.openstreetmap.org; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        return response

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
