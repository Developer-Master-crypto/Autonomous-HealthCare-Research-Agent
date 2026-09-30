"""Custom exceptions and centralized error response models."""

from typing import Any, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ResearchOpsException(Exception):
    """Base exception for all domain-specific ResearchOps errors."""

    def __init__(self, message: str, details: Optional[Any] = None):
        self.message = message
        self.details = details
        super().__init__(message)


class ResourceNotFoundError(ResearchOpsException):
    """Raised when a requested resource is not found."""
    pass


class ConfigurationError(ResearchOpsException):
    """Raised when an invalid configuration is detected."""
    pass


class DatabaseConnectionError(ResearchOpsException):
    """Raised when a database connection cannot be established or is lost."""
    pass


def register_exception_handlers(app: FastAPI) -> None:
    """Register centralized exception handlers for standard JSON error formats."""

    @app.exception_handler(ResearchOpsException)
    async def handle_domain_exception(request: Request, exc: ResearchOpsException) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "BAD_REQUEST",
                    "message": "The requested operation could not be completed.",
                    "details": None,
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request parameters or payload",
                    "details": [
                        {key: value for key, value in error.items() if key in {"loc", "msg", "type"}}
                        for error in exc.errors()
                    ],
                }
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected server error occurred.",
                }
            },
        )
