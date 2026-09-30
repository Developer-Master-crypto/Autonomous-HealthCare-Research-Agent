"""Provider-agnostic repository exports for the ResearchOps database layer."""

from backend.app.repositories.entity_repositories import (
    ConflictRepository,
    FacilityRepository,
    FacilityServiceRepository,
    GeographicObservationRepository,
    ResearchReportRepository,
    ServiceGapRepository,
    ServiceRepository,
)
from backend.app.repositories.research_repository import ResearchProjectRepository, ResearchTaskRepository
from backend.app.repositories.source_repository import ClaimEvidenceRepository, ClaimRepository, SourceRepository

__all__ = [
    "ClaimEvidenceRepository", "ClaimRepository", "ConflictRepository", "FacilityRepository",
    "FacilityServiceRepository", "GeographicObservationRepository", "ResearchProjectRepository",
    "ResearchReportRepository", "ResearchTaskRepository", "ServiceGapRepository", "ServiceRepository",
    "SourceRepository",
]
