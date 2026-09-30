"""Unit tests for ResearchOps business logic services and spatial algorithms."""

from backend.app.schemas.analysis import ConflictStatus, GapSeverity
from backend.app.schemas.facility import Facility, FacilityType
from backend.app.schemas.research import ResearchRequest, TaskStatus
from backend.app.schemas.source import ResearchClaim, SourceType
from backend.app.services import (
    GapAnalysisService,
    GeographicService,
    ReportService,
    ResearchService,
    SourceService,
    TaskPlannerService,
    VerificationService,
)


def test_task_planner_service():
    """Verify task planner decomposes query into ordered tasks."""
    planner = TaskPlannerService()
    tasks = planner.plan_tasks(
        research_id="test-res-123",
        query="Investigate pediatric burn unit capacities across the Midwest",
    )
    assert len(tasks) >= 4
    for idx, task in enumerate(tasks, start=1):
        assert task.research_id == "test-res-123"
        assert task.order == idx
        assert task.status == TaskStatus.PENDING
        assert len(task.title) > 0


def test_source_service():
    """Verify source registration, lookup, and listing."""
    svc = SourceService()
    source = svc.register_source(
        url="https://health.ohio.gov/reports/hospitals-2025.pdf",
        title="Ohio Department of Health 2025 Hospital Census",
        source_type=SourceType.GOVERNMENT_REGISTRY,
        publisher="Ohio Dept of Health",
        reliability_score=0.98,
    )
    assert source.id is not None
    assert source.url == "https://health.ohio.gov/reports/hospitals-2025.pdf"

    retrieved = svc.get_source(source.id)
    assert retrieved is not None
    assert retrieved.title == source.title

    all_sources = svc.list_sources()
    assert len(all_sources) == 1


def test_verification_service():
    """Verify conflict flagging and listing."""
    svc = VerificationService()
    claim_a = ResearchClaim(
        statement="Hospital operating 50 ICU beds according to CMS audit",
        source_url="https://cms.gov/hospitals/123",
        confidence=0.95,
        is_verified=True,
    )
    claim_b = ResearchClaim(
        statement="Hospital reduced ICU to 30 beds due to staffing",
        source_url="https://localnews.org/hospital-cuts",
        confidence=0.85,
        is_verified=False,
    )

    conflict = svc.flag_conflict(
        topic="ICU Bed Availability",
        claim_a=claim_a,
        claim_b=claim_b,
        description="CMS registry lists 50 beds while news indicates downsized 30 beds.",
    )
    assert conflict.id is not None
    assert conflict.resolution_status == ConflictStatus.UNRESOLVED
    assert len(svc.list_conflicts()) == 1


def test_geographic_service_haversine():
    """Verify Haversine distance calculations against known geodesic coordinates."""
    svc = GeographicService()

    # Coordinates: Columbus, OH (39.9612, -82.9988) to Cleveland, OH (41.4993, -81.6944)
    # Approximate straight-line distance is ~200 km
    dist = svc.calculate_haversine_distance(39.9612, -82.9988, 41.4993, -81.6944)
    assert 195.0 <= dist <= 210.0


def test_geographic_service_nearest_facility():
    """Verify nearest facility calculation."""
    svc = GeographicService()

    f1 = Facility(
        name="Metro Hospital",
        facility_type=FacilityType.ACUTE_CARE_HOSPITAL,
        latitude=40.0,
        longitude=-83.0,
    )
    f2 = Facility(
        name="Rural Health Center",
        facility_type=FacilityType.CRITICAL_ACCESS_HOSPITAL,
        latitude=41.0,
        longitude=-82.0,
    )
    svc.register_facility(f1)
    svc.register_facility(f2)

    # Point close to f1
    nearest_match = svc.find_nearest_facility(lat=40.05, lon=-83.02)
    assert nearest_match is not None
    facility, dist = nearest_match
    assert facility.name == "Metro Hospital"
    assert dist < 10.0


def test_gap_analysis_service():
    """Verify service gap recording and severity assessment."""
    svc = GapAnalysisService()

    assert svc.assess_severity_by_distance(100.0) == GapSeverity.CRITICAL
    assert svc.assess_severity_by_distance(65.0) == GapSeverity.HIGH
    assert svc.assess_severity_by_distance(40.0) == GapSeverity.MEDIUM
    assert svc.assess_severity_by_distance(15.0) == GapSeverity.LOW

    gap = svc.record_service_gap(
        region="Vinton County, OH",
        service_category="Obstetric / Maternal Care",
        description="No hospital with labor & delivery wing within 60 km radius",
        severity=GapSeverity.HIGH,
        affected_population_estimate=12000,
        nearest_facility_distance_km=62.5,
    )
    assert gap.id is not None
    assert len(svc.list_service_gaps()) == 1


def test_report_service():
    """Verify research dossier generation and retrieval."""
    svc = ReportService()
    report = svc.generate_report(
        research_id="res-abc-001",
        query="Evaluate neonatal ICU coverage",
        title="NICU Regional Infrastructure Report",
    )
    assert report.id is not None
    assert report.research_id == "res-abc-001"
    assert len(report.methodology_note) > 0

    fetched = svc.get_report(report.id)
    assert fetched is not None
    assert fetched.title == report.title


def test_research_service():
    """Verify master research session coordination."""
    svc = ResearchService()
    req = ResearchRequest(
        query="Assess psychiatric bed shortages across central Texas",
        region="Central Texas",
    )
    res = svc.create_research(req)
    assert res.research_id is not None
    assert res.query == req.query
    assert len(res.tasks) > 0

    session = svc.get_research(res.research_id)
    assert session is not None
    assert session.research_id == res.research_id
