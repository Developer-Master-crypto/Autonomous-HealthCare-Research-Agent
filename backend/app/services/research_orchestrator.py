"""Finite, evidence-first orchestration for the ResearchOps workflow."""

import re
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from backend.app.db.connection import DatabaseClient, MockDatabaseClient, get_database_client
from backend.app.models.db_models import (
    ResearchProjectModel,
    ResearchReportModel,
    ResearchTaskModel,
    SourceModel,
)
from backend.app.repositories.entity_repositories import ResearchReportRepository
from backend.app.repositories.research_repository import (
    ResearchProjectRepository,
    ResearchTaskRepository,
)
from backend.app.schemas.analysis import Conflict
from backend.app.schemas.facility import Facility, Service
from backend.app.schemas.research import (
    ResearchProgress,
    ResearchRequest,
    ResearchResponse,
    ResearchStatus,
    TaskStatus,
)
from backend.app.schemas.service_gap_analysis import ServiceAvailabilityEvidence
from backend.app.schemas.source import ResearchClaim, ResearchSource
from backend.app.schemas.verification import (
    ClaimEvidenceRecord,
    EvidenceRelation,
    VerifiableClaim,
    VerificationStatus,
)
from backend.app.services.facility_extraction_service import FacilityExtractionService
from backend.app.services.gap_analysis_service import GapAnalysisService
from backend.app.services.geographic_service import GeographicService
from backend.app.services.report_service import ReportService
from backend.app.services.task_planner_service import TaskPlannerService
from backend.app.services.verification_service import VerificationService


class ResearchOrchestrator:
    """Coordinate the research pipeline with explicit limits and progress."""

    def __init__(self, task_planner=None, search_service=None, content_extractor=None,
                 facility_extractor=None, geographic_service=None, gap_analysis_service=None,
                 report_service=None, max_tasks: int = 10, max_follow_up_tasks: int = 2,
                 verification_service=None, database_client: Optional[DatabaseClient] = None,
                 execution_mode: Optional[str] = None) -> None:
        if max_tasks < 1 or max_follow_up_tasks < 0:
            raise ValueError("Research limits must allow at least one task and no negative follow-ups.")
        self.task_planner = task_planner or TaskPlannerService()
        self.search_service = search_service
        self.content_extractor = content_extractor
        self.facility_extractor = facility_extractor or FacilityExtractionService()
        self.geographic_service = geographic_service or GeographicService()
        self.gap_analysis_service = gap_analysis_service or GapAnalysisService()
        self.report_service = report_service or ReportService()
        self.verification_service = verification_service or VerificationService()
        self.database_client = database_client or get_database_client()
        self.project_repository = ResearchProjectRepository(self.database_client)
        self.task_repository = ResearchTaskRepository(self.database_client)
        self.report_repository = ResearchReportRepository(self.database_client)
        self.execution_mode = execution_mode or ("mock" if isinstance(self.database_client, MockDatabaseClient) and search_service else "unconfigured")
        self.max_tasks = max_tasks
        self.max_follow_up_tasks = max_follow_up_tasks
        self._projects: Dict[str, ResearchResponse] = {}
        self._source_cache: Dict[str, SourceModel] = {}

    async def run(self, request: ResearchRequest) -> ResearchResponse:
        """Create a project and execute each pipeline stage in a controlled order."""
        task_limit = self._limit(request.parameters, "max_tasks", self.max_tasks, 1, self.max_tasks)
        follow_limit = self._limit(request.parameters, "max_follow_up_tasks", self.max_follow_up_tasks, 0, self.max_follow_up_tasks)
        area, radius = self._query_geography(request)
        project = ResearchResponse(query=request.query, region=area, status=ResearchStatus.CREATED,
                                  execution_mode=self.execution_mode)
        project.progress = ResearchProgress(current_stage="QUESTION UNDERSTANDING", tasks_limit=task_limit)
        self._projects[project.research_id] = project
        self._persist_project(project)
        try:
            project.status = ResearchStatus.PLANNING
            project.progress.current_stage = "TASK DECOMPOSITION"
            project.tasks = self.task_planner.plan_tasks(project.research_id, request.query)[:task_limit]
            sources = await self._search_and_extract(project, follow_limit)
            facilities, services, evidence, claims, conflicts = self._extract_entities(sources, project)
            project.intermediate_results.update({
                "source_count": len(sources),
                "facility_count": len(facilities),
                "service_count": len(services),
                "evidence_count": len(evidence),
            })
            project.status = ResearchStatus.VERIFYING
            project.progress.current_stage = "EVIDENCE VERIFICATION"
            if self.search_service is not None:
                project.progress.completed_stages.append("SEARCH")
                if self.content_extractor is not None:
                    project.progress.completed_stages.append("SOURCE EXTRACTION")
            project.progress.completed_stages.extend(["FACILITY/SERVICE EXTRACTION", "EVIDENCE COLLECTION"])
            project.progress.completed_stages.append("EVIDENCE VERIFICATION")
            project.progress.current_stage = "CONFLICT DETECTION"
            project.progress.completed_stages.append("CONFLICT DETECTION")
            project.status = ResearchStatus.ANALYZING
            project.progress.current_stage = "GEOGRAPHIC ANALYSIS"
            distances = self._analyse_geography(project, facilities, radius)
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
                executive_summary=(f"{project.execution_mode.title()}-mode evidence review returned {len(sources)} sources, "
                                   f"{len(facilities)} facility records, and {len(assessments)} service availability assessments. "
                                   "Results are limited to the retrieved evidence and listed limitations."),
                facilities=facilities, sources=[self._as_source(source) for source in sources],
                claims=claims, conflicts=conflicts,
            )
            project.report_id = report.id
            project.status = ResearchStatus.COMPLETED
            project.progress.current_stage = "COMPLETED"
            project.progress.completed_stages.append("REPORT GENERATION")
        except Exception:
            project.status = ResearchStatus.FAILED
            project.error = "Research could not be completed. State was retained for review."
            project.missing_information.append("A processing stage failed; no unsupported findings were generated.")
            project.progress.current_stage = "FAILED"
        project.updated_at = datetime.now(timezone.utc)
        self._persist_final(project)
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
            project.progress.skipped_stages.extend(["SEARCH", "SOURCE EXTRACTION"])
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
        if not sources:
            project.missing_information.append("No search sources were returned; findings were not inferred from absent results.")
        project.progress.current_stage = "SOURCE EXTRACTION"
        if self.content_extractor is None:
            if sources:
                project.missing_information.append("Source content extraction is not configured; only source metadata is available.")
            project.progress.skipped_stages.append("SOURCE EXTRACTION")
            return sources
        extracted = []
        for source in sources:
            try:
                extracted.append(await self.content_extractor.extract_and_store(source))
            except Exception:
                project.missing_information.append(f"Source extraction failed for '{source.url}'; no extracted findings were used.")
        return extracted

    def _extract_entities(self, sources: List[SourceModel], project: ResearchResponse):
        facilities, services, evidence, claims = [], [], [], []
        assertion_evidence = {}
        source_by_url = {source.url.rstrip("/"): source for source in sources}
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
                        source_url=extracted_service.evidence.source_url, source_title=extracted_service.evidence.source_title,
                        availability_confirmed=extracted_service.availability_confirmed))
                    statement = f"{facility.name} {'offers' if extracted_service.availability_confirmed else 'does not offer'} {name}."
                    assertion = f"{facility.name} offers {name}."
                    record = ClaimEvidenceRecord(
                        evidence_text=extracted_service.evidence.supporting_text,
                        source_id=source_by_url.get(extracted_service.evidence.source_url.rstrip("/"), SourceModel(url=extracted_service.evidence.source_url, title=extracted_service.evidence.source_title)).id,
                        source_url=extracted_service.evidence.source_url,
                        source_title=extracted_service.evidence.source_title,
                        relation=EvidenceRelation.SUPPORTS if extracted_service.availability_confirmed else EvidenceRelation.CONTRADICTS,
                    )
                    assertion_evidence.setdefault(assertion, []).append((statement, record))
        conflicts = []
        for index, (assertion, items) in enumerate(assertion_evidence.items()):
            verified = self.verification_service.verify_claim(
                VerifiableClaim(id=f"{project.research_id}-claim-{index + 1}", claim_text=assertion),
                [record for _, record in items],
            )
            for statement, record in items:
                claims.append(ResearchClaim(
                    statement=statement, source_id=record.source_id, source_url=record.source_url,
                    is_verified=verified.status == VerificationStatus.SUPPORTED,
                ))
            for conflict in verified.conflicts:
                positive = next(((statement, record) for statement, record in items if record.relation == EvidenceRelation.SUPPORTS), None)
                negative = next(((statement, record) for statement, record in items if record.relation == EvidenceRelation.CONTRADICTS), None)
                if positive and negative:
                    claims_by_statement = {claim.statement: claim for claim in claims}
                    conflicts.append(Conflict(
                        topic=assertion, claim_a=claims_by_statement[positive[0]], claim_b=claims_by_statement[negative[0]],
                        description="Sources provide explicit contradictory statements; both are retained for review.",
                    ))
        project.intermediate_results["evidence_status"] = {
            "supported": sum(claim.is_verified for claim in claims),
            "conflicting": len(conflicts),
            "insufficient_evidence": sum(not claim.is_verified for claim in claims) - 2 * len(conflicts),
        }
        if sources and not facilities:
            project.missing_information.append("No facilities or services could be extracted from retrieved source content.")
        return facilities, services, evidence, claims, conflicts

    def _analyse_geography(self, project: ResearchResponse, facilities: List[Facility], radius_km: Optional[float] = None):
        if not project.region:
            project.missing_information.append("No target area was supplied for geographic analysis.")
            return None
        result = self.geographic_service.analyse(project.region, facilities=facilities, radius_km=radius_km)
        project.missing_information.extend(result.warnings)
        project.intermediate_results["geographic_analysis"] = result.to_map_json()
        return result.facilities_inside_radius + result.facilities_outside_radius

    @staticmethod
    def _query_geography(request: ResearchRequest):
        match = re.search(r"\bwithin\s+(\d+(?:\.\d+)?)\s*km\s+of\s+([^,.?]+)", request.query, re.IGNORECASE)
        inferred_area = re.split(r"\s+and\s+", match.group(2).strip(), maxsplit=1, flags=re.IGNORECASE)[0] if match else None
        if request.region:
            return request.region, float(match.group(1)) if match else None
        return (inferred_area, float(match.group(1))) if match else (None, None)

    def _persist_project(self, project: ResearchResponse) -> None:
        try:
            metadata = {"execution_mode": project.execution_mode, "research_id": project.research_id}
            self.project_repository.create(ResearchProjectModel(
                id=project.research_id, user_query=project.query, status=project.status.value,
                region=project.region, metadata=metadata, created_at=project.created_at,
            ))
        except Exception:
            project.intermediate_results["persistence_status"] = "unavailable"
            project.missing_information.append("Database persistence is unavailable; research remains in process memory only.")

    def _persist_final(self, project: ResearchResponse) -> None:
        try:
            existing = self.project_repository.get_by_id(project.research_id)
            if existing:
                self.project_repository.update(project.research_id, {
                    "status": project.status.value, "region": project.region,
                    "metadata": {"execution_mode": project.execution_mode,
                                 "intermediate_results": project.intermediate_results,
                                 "missing_information": project.missing_information,
                                 "report_id": project.report_id},
                })
            for task in project.tasks:
                if not self.task_repository.get_by_id(task.id):
                    self.task_repository.create(ResearchTaskModel(
                        id=task.id, research_project_id=project.research_id, task_type=task.title,
                        description=task.description, status=task.status.value, priority=task.order,
                        created_at=task.created_at,
                    ))
            report = self.report_service.get_report_by_research_id(project.research_id)
            if report:
                if not self.report_repository.get_by_id(report.id):
                    self.report_repository.create(ResearchReportModel(
                        id=report.id, research_project_id=project.research_id,
                        title=report.title, content=report.model_dump(mode="json"),
                        created_at=report.generated_at,
                    ))
            if project.intermediate_results.get("persistence_status") != "unavailable":
                project.intermediate_results["persistence_status"] = "mock_memory" if isinstance(self.database_client, MockDatabaseClient) else "database"
        except Exception:
            project.intermediate_results["persistence_status"] = "unavailable"
            project.missing_information.append("Database persistence was incomplete; in-memory research state was retained.")

    @staticmethod
    def _limit(parameters, key, default, minimum, maximum):
        value = (parameters or {}).get(key, default)
        return value if isinstance(value, int) and minimum <= value <= maximum else default

    @staticmethod
    def _as_source(source: SourceModel) -> ResearchSource:
        return ResearchSource(id=source.id, url=source.url, title=source.title, source_type=source.source_type,
                              publisher=source.publisher, retrieved_at=source.retrieved_at)
