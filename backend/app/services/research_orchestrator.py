"""Finite, evidence-first orchestration for the ResearchOps workflow."""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from backend.app.models.db_models import SourceModel
from backend.app.schemas.facility import Facility, Service
from backend.app.schemas.research import ResearchProgress, ResearchRequest, ResearchResponse, ResearchStatus, TaskStatus
from backend.app.schemas.service_gap_analysis import ServiceAvailabilityEvidence
from backend.app.schemas.source import ResearchSource
from backend.app.services.facility_extraction_service import FacilityExtractionService
from backend.app.services.gap_analysis_service import GapAnalysisService
from backend.app.services.geographic_service import GeographicService
from backend.app.services.report_service import ReportService
from backend.app.services.task_planner_service import TaskPlannerService


class ResearchOrchestrator:
    """Coordinate the research pipeline with explicit limits and progress."""

    def __init__(self, task_planner=None, search_service=None, content_extractor=None,
                 facility_extractor=None, geographic_service=None, gap_analysis_service=None,
                 report_service=None, max_tasks: int = 10, max_follow_up_tasks: int = 2) -> None:
        if max_tasks < 1 or max_follow_up_tasks < 0:
            raise ValueError("Research limits must allow at least one task and no negative follow-ups.")
        self.task_planner = task_planner or TaskPlannerService()
        self.search_service = search_service
        self.content_extractor = content_extractor
        self.facility_extractor = facility_extractor or FacilityExtractionService()
        self.geographic_service = geographic_service or GeographicService()
        self.gap_analysis_service = gap_analysis_service or GapAnalysisService()
        self.report_service = report_service or ReportService()
        self.max_tasks = max_tasks
        self.max_follow_up_tasks = max_follow_up_tasks
        self._projects: Dict[str, ResearchResponse] = {}
        self._source_cache: Dict[str, SourceModel] = {}

    async def run(self, request: ResearchRequest) -> ResearchResponse:
        """Create a project and execute each pipeline stage in a controlled order."""
        task_limit = self._limit(request.parameters, "max_tasks", self.max_tasks, 1, self.max_tasks)
        follow_limit = self._limit(request.parameters, "max_follow_up_tasks", self.max_follow_up_tasks, 0, self.max_follow_up_tasks)
        project = ResearchResponse(query=request.query, region=request.region, status=ResearchStatus.CREATED)
        project.progress = ResearchProgress(current_stage="QUESTION UNDERSTANDING", tasks_limit=task_limit)
        self._projects[project.research_id] = project
        try:
            project.status = ResearchStatus.PLANNING
            project.progress.current_stage = "TASK DECOMPOSITION"
            project.tasks = self.task_planner.plan_tasks(project.research_id, request.query)[:task_limit]
            sources = await self._search_and_extract(project, follow_limit)
            facilities, services, evidence = self._extract_entities(sources, project)
            project.intermediate_results.update({
                "source_count": len(sources),
                "facility_count": len(facilities),
                "service_count": len(services),
                "evidence_count": len(evidence),
            })
            project.status = ResearchStatus.VERIFYING
            project.progress.current_stage = "CONFLICT DETECTION"
            project.progress.completed_stages.extend(["SEARCH", "SOURCE EXTRACTION", "FACILITY/SERVICE EXTRACTION", "EVIDENCE COLLECTION", "CONFLICT DETECTION"])
            project.status = ResearchStatus.ANALYZING
            project.progress.current_stage = "GEOGRAPHIC ANALYSIS"
            distances = self._analyse_geography(project, facilities)
            assessments = self.gap_analysis_service.analyze_services_availability(
                project.region or "Unspecified area", facilities, services, evidence, distances
            ) if services else []
            project.intermediate_results["service_gap_assessment_count"] = len(assessments)
            project.intermediate_results["service_gap_assessments"] = [
                assessment.model_dump(mode="json") for assessment in assessments
            ]
            project.progress.completed_stages.extend(["GEOGRAPHIC ANALYSIS", "SERVICE GAP ANALYSIS"])
            project.status = ResearchStatus.REPORTING
            project.progress.current_stage = "REPORT GENERATION"
            report = self.report_service.generate_report(
                research_id=project.research_id, query=project.query,
                executive_summary=(f"Bounded evidence review completed with {project.progress.sources_retrieved} retrieved sources "
                                   f"and {len(assessments)} service availability assessments. Findings reflect collected evidence and limitations."),
                facilities=facilities, sources=[self._as_source(source) for source in sources],
            )
            project.report_id = report.id
            project.status = ResearchStatus.COMPLETED
            project.progress.current_stage = "COMPLETED"
            project.progress.completed_stages.append("REPORT GENERATION")
        except Exception as exc:
            project.status = ResearchStatus.FAILED
            project.error = "Research could not be completed. State was retained for review."
            project.missing_information.append("A processing stage failed; no unsupported findings were generated.")
            project.progress.current_stage = "FAILED"
        project.updated_at = datetime.now(timezone.utc)
        return project

    def get_project(self, research_id: str) -> Optional[ResearchResponse]:
        return self._projects.get(research_id)

    def list_projects(self) -> List[ResearchResponse]:
        return list(self._projects.values())

    async def _search_and_extract(self, project: ResearchResponse, follow_limit: int) -> List[SourceModel]:
        project.status = ResearchStatus.RESEARCHING
        project.progress.current_stage = "SEARCH"
        if self.search_service is None:
            project.missing_information.append("Search is not configured; no external sources were retrieved.")
            return []
        sources: List[SourceModel] = []
        for task in project.tasks:
            task.status = TaskStatus.IN_PROGRESS
            try:
                for result in await self.search_service.search_task(task):
                    key = result.url.rstrip("/")
                    source = self._source_cache.get(key)
                    if source is None:
                        source = SourceModel(url=result.url, title=result.title, domain=result.domain,
                                             source_type=result.source_type.value, snippet=result.snippet,
                                             retrieved_at=result.retrieved_at)
                        self._source_cache[key] = source
                        project.progress.sources_retrieved += 1
                    else:
                        project.progress.sources_reused += 1
                    if source not in sources:
                        sources.append(source)
                task.status = TaskStatus.COMPLETED
            except Exception:
                task.status = TaskStatus.FAILED
                project.missing_information.append(f"Search failed for task '{task.title}'; the provider did not return results.")
            project.progress.tasks_completed += 1
        if not sources and follow_limit:
            follow_up = project.tasks[:follow_limit]
            for task in follow_up:
                project.tasks.append(task.model_copy(update={
                    "id": str(uuid4()),
                    "title": f"Follow-up: {task.title}",
                    "description": f"Find an independent source for: {task.description}",
                    "order": len(project.tasks) + 1,
                    "status": TaskStatus.PENDING,
                }))
            project.progress.follow_up_tasks_created = len(follow_up)
            project.missing_information.append("Follow-up search creation stopped at the configured research limit.")
        project.progress.current_stage = "SOURCE EXTRACTION"
        if self.content_extractor is None:
            if sources:
                project.missing_information.append("Source content extraction is not configured; only source metadata is available.")
            return sources
        extracted = []
        for source in sources:
            try:
                extracted.append(await self.content_extractor.extract_and_store(source))
            except Exception:
                project.missing_information.append(f"Source extraction failed for '{source.url}'; no extracted findings were used.")
        return extracted

    def _extract_entities(self, sources: List[SourceModel], project: ResearchResponse):
        facilities, services, evidence = [], [], []
        for source in sources:
            for item in self.facility_extractor.extract(source).facilities:
                facility = Facility(
                    name=item.name, address=item.address, city=item.city, state=item.state,
                    latitude=item.latitude, longitude=item.longitude,
                    metadata={
                        "source_evidence": {
                            "source_url": item.evidence.source_url,
                            "source_title": item.evidence.source_title,
                        },
                        "services": [
                            service.healthcare_service or service.specialty or service.department
                            for service in item.services
                            if service.healthcare_service or service.specialty or service.department
                        ],
                    },
                )
                facilities.append(facility)
                for extracted_service in item.services:
                    name = extracted_service.healthcare_service or extracted_service.specialty or extracted_service.department
                    if not name:
                        continue
                    services.append(Service(facility_id=facility.id, name=name, category="extracted"))
                    evidence.append(ServiceAvailabilityEvidence(facility_id=facility.id, facility_name=facility.name,
                        service=name, evidence_text=extracted_service.evidence.supporting_text,
                        source_url=extracted_service.evidence.source_url, source_title=extracted_service.evidence.source_title))
        if sources and not facilities:
            project.missing_information.append("No facilities or services could be extracted from retrieved source content.")
        return facilities, services, evidence

    def _analyse_geography(self, project: ResearchResponse, facilities: List[Facility]):
        if not project.region:
            project.missing_information.append("No target area was supplied for geographic analysis.")
            return None
        result = self.geographic_service.analyse(project.region, facilities=facilities)
        project.missing_information.extend(result.warnings)
        project.intermediate_results["geographic_analysis"] = result.to_map_json()
        return result.facilities_inside_radius + result.facilities_outside_radius

    @staticmethod
    def _limit(parameters, key, default, minimum, maximum):
        value = (parameters or {}).get(key, default)
        return value if isinstance(value, int) and minimum <= value <= maximum else default

    @staticmethod
    def _as_source(source: SourceModel) -> ResearchSource:
        return ResearchSource(id=source.id, url=source.url, title=source.title, source_type=source.source_type,
                              publisher=source.publisher, retrieved_at=source.retrieved_at)
