"""Tests for evidence-backed healthcare facility extraction and normalization."""

from backend.app.models.db_models import SourceModel
from backend.app.schemas.facility_extraction import ExtractedFacility, SourceEvidence
from backend.app.services.entity_normalization_service import EntityNormalizationService
from backend.app.services.facility_extraction_service import FacilityExtractionService


def source(text: str, status: str = "success") -> SourceModel:
    return SourceModel(
        url="https://whitefield.example/facilities",
        title="Whitefield Health Directory",
        domain="whitefield.example",
        extraction_status=status,
        extracted_text=text,
    )


def test_extracts_only_explicit_facility_fields_and_evidence():
    result = FacilityExtractionService().extract(source(
        "Whitefield Cardiac Hospital offers a Cardiology Department and cardiac care. "
        "Address: 12 Main Road. City: Bengaluru. State: Karnataka. Country: India. "
        "Latitude: 12.9698 Longitude: 77.7500. Website: https://whitefieldcardiac.example Phone: +91 80 1234 5678"
    ))

    facility = result.facilities[0]
    assert facility.name == "Whitefield Cardiac Hospital"
    assert facility.city == "Bengaluru"
    assert facility.latitude == 12.9698
    assert facility.website == "https://whitefieldcardiac.example"
    assert facility.services[0].evidence.source_url == result.source_url
    assert "Cardiology Department" in facility.services[0].evidence.supporting_text


def test_unavailable_fields_stay_null_and_inaccessible_source_is_not_analyzed():
    result = FacilityExtractionService().extract(source("", status="restricted"))
    assert result.facilities == []

    supported = FacilityExtractionService().extract(source("Metro Hospital is open."))
    assert supported.facilities[0].address is None
    assert supported.facilities[0].services == []


def test_services_require_direct_source_evidence():
    result = FacilityExtractionService().extract(source("Metro Hospital provides oncology services."))
    service = result.facilities[0].services[0]
    assert service.healthcare_service == "oncology"
    assert service.evidence.supporting_text == "Metro Hospital provides oncology services."


def test_directory_page_never_shares_coordinates_between_facilities():
    result = FacilityExtractionService().extract(source(
        "Alpha Cardiac Hospital provides cardiology at Latitude: 12 Longitude: 77, Address: 1 A Road. "
        "Beta Medical Center provides cardiology at Latitude: 13 Longitude: 78, Address: 2 B Road."
    ))
    alpha, beta = result.facilities
    assert (alpha.latitude, alpha.longitude) == (12, 77)
    assert (beta.latitude, beta.longitude) == (13, 78)


def test_normalizer_requires_exact_name_and_identity_anchor_before_merging():
    evidence = SourceEvidence(supporting_text="Metro Hospital", source_url="https://example.org", source_title="Directory")
    existing = ExtractedFacility(name="Metro Hospital", address="1 Main Street", evidence=evidence)
    same = ExtractedFacility(name="Metro Hospital", address="1 Main Street", evidence=evidence)
    similar = ExtractedFacility(name="Metro Hospitals", address="1 Main Street", evidence=evidence)
    name_only = ExtractedFacility(name="Metro Hospital", evidence=evidence)
    normalizer = EntityNormalizationService()

    assert normalizer.compare(same, existing).should_merge is True
    assert normalizer.compare(similar, existing).should_merge is False
    assert normalizer.compare(name_only, existing).should_merge is False
