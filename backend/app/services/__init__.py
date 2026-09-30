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
from backend.app.core.config import settings
from backend.app.db.connection import get_database_client
from backend.app.repositories.source_repository import SourceRepository
from backend.app.services.content_extractor import ContentExtractor
from backend.app.services.source_fetcher import SourceFetcher
from backend.app.services.search_service import SearchService

# Shared singleton service instances
task_planner_service = TaskPlannerService()
source_service = SourceService()
verification_service = VerificationService()
geographic_service = GeographicService()
gap_analysis_service = GapAnalysisService()
report_service = ReportService()
research_service = ResearchService(task_planner=task_planner_service)
database_client = get_database_client()
source_repository = SourceRepository(database_client)
search_service = SearchService(source_repository=source_repository) if settings.TAVILY_API_KEY else None
content_extractor = ContentExtractor(
    SourceFetcher(timeout_seconds=settings.SOURCE_FETCH_TIMEOUT_SECONDS), source_repository,
    max_content_chars=settings.MAX_SOURCE_CONTENT_CHARS,
)
research_orchestrator = ResearchOrchestrator(
    task_planner=task_planner_service,
    search_service=search_service,
    content_extractor=content_extractor,
    report_service=report_service,
    database_client=database_client,
    execution_mode="live" if search_service else "unconfigured",
)

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
