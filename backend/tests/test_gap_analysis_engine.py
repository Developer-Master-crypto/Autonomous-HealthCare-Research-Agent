"""Tests for cautious, evidence-limited healthcare service-gap analysis."""

from backend.app.schemas.facility import Facility, Service
from backend.app.schemas.service_gap_analysis import ServiceAvailabilityEvidence, ServiceGapStatus
from backend.app.services.distance_service import FacilityDistance
from backend.app.services.gap_analysis_service import GapAnalysisService


def facility(name: str) -> Facility:
    return Facility(name=name, latitude=12.0, longitude=77.0)


def evidence(facility: Facility, confirmed: bool = True) -> ServiceAvailabilityEvidence:
    return ServiceAvailabilityEvidence(
        facility_id=facility.id,
        facility_name=facility.name,
        service="cardiology",
        evidence_text=f"{facility.name} lists cardiology services.",
        source_url=f"https://{facility.name.lower().replace(' ', '')}.example/services",
        source_title="Facility service directory",
        availability_confirmed=confirmed,
    )


def test_single_documented_facility_uses_limited_availability_language():
    first = facility("North Hospital")
    result = GapAnalysisService().analyze_service_availability("Whitefield", "cardiology", [first], [evidence(first)])
    assert result.status == ServiceGapStatus.COMPARATIVELY_LIMITED_AVAILABILITY
    assert result.number_of_facilities_providing_service == 1
    assert "Comparatively limited availability" in result.summary


def test_multiple_documented_facilities_are_not_presented_as_a_gap():
    first, second = facility("North Hospital"), facility("South Hospital")
    result = GapAnalysisService().analyze_service_availability(
        "Whitefield", "cardiology", [first, second], [evidence(first), evidence(second)]
    )
    assert result.status == ServiceGapStatus.AVAILABILITY_DOCUMENTED
    assert result.number_of_facilities_providing_service == 2


def test_no_evidence_is_insufficient_not_a_claim_of_absence():
    result = GapAnalysisService().analyze_service_availability("Whitefield", "cardiology", [facility("North Hospital")], [])
    assert result.status == ServiceGapStatus.INSUFFICIENT_EVIDENCE
    assert "definitely no service" not in result.summary.casefold()


def test_unconfirmed_evidence_creates_a_cautious_potential_gap():
    first = facility("North Hospital")
    result = GapAnalysisService().analyze_service_availability("Whitefield", "cardiology", [first], [evidence(first, confirmed=False)])
    assert result.status == ServiceGapStatus.POTENTIAL_SERVICE_GAP
    assert result.number_of_facilities_providing_service == 0
    assert "Potential service gap" in result.summary


def test_distance_filter_and_missing_location_data_are_limitations():
    inside, outside, missing = facility("Near Hospital"), facility("Far Hospital"), Facility(name="Unknown Hospital")
    distances = [
        FacilityDistance(inside, 2, 0, inside_radius=True),
        FacilityDistance(outside, 80, 0, inside_radius=False),
    ]
    result = GapAnalysisService().analyze_service_availability(
        "Whitefield", "cardiology", [inside, outside, missing], [evidence(inside), evidence(outside)], distances
    )
    assert result.supporting_facilities == ["Near Hospital"]
    assert any("coordinates" in limitation for limitation in result.limitations)


def test_unmatched_confirming_evidence_is_preserved_as_a_limitation():
    result = GapAnalysisService().analyze_service_availability(
        "Whitefield",
        "cardiology",
        [facility("North Hospital")],
        [
            ServiceAvailabilityEvidence(
                facility_name="Unlisted Hospital",
                service="cardiology",
                evidence_text="Cardiology is listed.",
                source_url="https://unlisted.example/services",
                source_title="Facility service directory",
            )
        ],
    )
    assert result.number_of_facilities_providing_service == 0
    assert len(result.evidence) == 1
    assert any("could not be matched" in limitation for limitation in result.limitations)


def test_multiple_service_assessments_use_supplied_service_list():
    first = facility("North Hospital")
    services = [
        Service(facility_id=first.id, name="cardiology", category="specialty"),
        Service(facility_id=first.id, name="oncology", category="specialty"),
    ]
    results = GapAnalysisService().analyze_services_availability(
        "Whitefield", [first], services, [evidence(first)]
    )
    assert [result.service for result in results] == ["cardiology", "oncology"]
    assert results[0].status == ServiceGapStatus.COMPARATIVELY_LIMITED_AVAILABILITY
    assert results[1].status == ServiceGapStatus.INSUFFICIENT_EVIDENCE
