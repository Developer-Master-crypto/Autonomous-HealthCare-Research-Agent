"""Services package containing business logic, analytical engines, and service abstractions."""

from backend.app.services.llm_base import BaseLLMService
from backend.app.services.task_planner_service import TaskPlannerService
from backend.app.services.source_service import SourceService
from backend.app.services.verification_service import VerificationService
from backend.app.services.geographic_service import GeographicService
from backend.app.services.distance_service import DistanceService, FacilityDistance, GeographicAnalysisResult
from backend.app.services.geocoding_provider import (
    BaseGeocodingProvider,
    MockGeocodingProvider,
    NominatimGeocodingProvider,
    get_geocoding_provider,
)
from backend.app.services.gap_analysis_service import GapAnalysisService
from backend.app.services.report_service import ReportService
from backend.app.services.research_service import ResearchService
from backend.app.services.research_orchestrator import ResearchOrchestrator

# Shared singleton service instances
task_planner_service = TaskPlannerService()
source_service = SourceService()
verification_service = VerificationService()
geographic_service = GeographicService()
gap_analysis_service = GapAnalysisService()
report_service = ReportService()
research_service = ResearchService(task_planner=task_planner_service)
research_orchestrator = ResearchOrchestrator(task_planner=task_planner_service)

__all__ = [
    "BaseLLMService",
    "TaskPlannerService",
    "SourceService",
    "VerificationService",
    "GeographicService",
    "DistanceService",
    "FacilityDistance",
    "GeographicAnalysisResult",
    "BaseGeocodingProvider",
    "MockGeocodingProvider",
    "NominatimGeocodingProvider",
    "get_geocoding_provider",
    "GapAnalysisService",
    "ReportService",
    "ResearchService",
    "ResearchOrchestrator",
    "task_planner_service",
    "source_service",
    "verification_service",
    "geographic_service",
    "gap_analysis_service",
    "report_service",
    "research_service",
    "research_orchestrator",
]
