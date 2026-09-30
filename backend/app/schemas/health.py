"""Pydantic schemas for system health and diagnostics."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema for /api/health response."""

    status: str = Field(
        default="ok",
        description="Current health status of the application",
        examples=["ok"],
    )
    service: str = Field(
        default="researchops-api",
        description="Name of the reporting service",
        examples=["researchops-api"],
    )
