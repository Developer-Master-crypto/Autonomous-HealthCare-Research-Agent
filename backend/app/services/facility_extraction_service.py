"""Conservative, evidence-first facility and service extraction from source text."""

import re
from typing import Dict, List

from backend.app.models.db_models import SourceModel
from backend.app.schemas.facility_extraction import (
    ExtractedFacility,
    ExtractedHealthcareService,
    FacilityExtractionResult,
    SourceEvidence,
)


class FacilityExtractionService:
    """Extract only explicit facility facts and service mentions from successful sources."""

    _facility_pattern = re.compile(
        r"\b([A-Z][A-Za-z0-9&'(). -]{1,80}?(?:Hospital|Medical Center|Medical Centre|Clinic|Health Center|Health Centre))\b"
    )
    _label_patterns: Dict[str, re.Pattern] = {
        "address": re.compile(r"\bAddress\s*:\s*([^\n.]+)", re.IGNORECASE),
        "city": re.compile(r"\bCity\s*:\s*([^\n,.]+)", re.IGNORECASE),
        "state": re.compile(r"\bState\s*:\s*([^\n,.]+)", re.IGNORECASE),
        "country": re.compile(r"\bCountry\s*:\s*([^\n,.]+)", re.IGNORECASE),
        "website": re.compile(r"\b(?:Website|Web)\s*:\s*(https?://[^\s,]+)", re.IGNORECASE),
        "phone": re.compile(r"\b(?:Phone|Tel(?:ephone)?|Contact)\s*:\s*([+()0-9][+()0-9 .-]{5,})", re.IGNORECASE),
    }
    _coordinates_pattern = re.compile(
        r"\bLatitude\s*:\s*(-?\d{1,2}(?:\.\d+)?)\s*[,;]?\s*Longitude\s*:\s*(-?\d{1,3}(?:\.\d+)?)",
        re.IGNORECASE,
    )
    _service_pattern = re.compile(
        r"\b(cardiology|cardiac care|oncology|pediatrics?|emergency medicine|trauma care|maternity|obstetrics|neurology|orthopedics?|dialysis|radiology|surgery)\b",
        re.IGNORECASE,
    )
    _department_pattern = re.compile(r"\b([A-Za-z ]{2,50}\bDepartment)\b", re.IGNORECASE)

    def extract(self, source: SourceModel) -> FacilityExtractionResult:
        """Return only facilities and services demonstrably present in extracted text."""
        if source.extraction_status != "success" or not source.extracted_text:
            return FacilityExtractionResult(source_url=source.url, source_title=source.title)

        facilities: List[ExtractedFacility] = []
        seen_names = set()
        text = source.extracted_text
        matches = list(self._facility_pattern.finditer(text))
        # Page-wide metadata is safe only when the page identifies one facility.
        # On directory pages, only attach attributes found in the facility's own
        # sentence; otherwise nearby hospitals can inherit each other's details.
        unique_facilities = len({
            match.group(1).strip().casefold() for match in matches
        })
        page_attributes = self._extract_attributes(text) if unique_facilities == 1 else {}
        for match in matches:
            name = match.group(1).strip()
            normalized_name = name.casefold()
            if normalized_name in seen_names:
                continue
            seen_names.add(normalized_name)
            sentence = self._sentence_for_offset(text, match.start(), match.end())
            if unique_facilities > 1:
                next_facility = next((candidate.start() for candidate in matches if candidate.start() > match.start()), len(text))
                sentence = text[match.start():next_facility].strip()
                sentence = self._sentence_for_offset(sentence, 0, len(sentence))
            attributes = page_attributes if unique_facilities == 1 else self._extract_attributes(sentence)
            # Attribute services only when they occur in the same sentence as the
            # facility mention; page-wide co-occurrence is not sufficient evidence.
            services = self._extract_services(sentence, source.url, source.title)
            facility_evidence = SourceEvidence(
                source_url=source.url,
                source_title=source.title,
                supporting_text=sentence,
            )
            facilities.append(ExtractedFacility(name=name, evidence=facility_evidence, services=services, **attributes))
        return FacilityExtractionResult(source_url=source.url, source_title=source.title, facilities=facilities)

    def _extract_attributes(self, text: str) -> Dict[str, object]:
        attributes: Dict[str, object] = {}
        for field, pattern in self._label_patterns.items():
            match = pattern.search(text)
            if match:
                attributes[field] = match.group(1).strip()
        coordinate_match = self._coordinates_pattern.search(text)
        if coordinate_match:
            latitude, longitude = map(float, coordinate_match.groups())
            if -90 <= latitude <= 90 and -180 <= longitude <= 180:
                attributes["latitude"] = latitude
                attributes["longitude"] = longitude
        return attributes

    def _extract_services(self, text: str, source_url: str, source_title: str) -> List[ExtractedHealthcareService]:
        services: List[ExtractedHealthcareService] = []
        seen = set()
        for match in self._service_pattern.finditer(text):
            sentence = self._sentence_for_offset(text, match.start(), match.end())
            service_name = match.group(1).strip()
            department_match = self._department_pattern.search(sentence)
            key = (service_name.casefold(), sentence)
            if key in seen:
                continue
            seen.add(key)
            services.append(ExtractedHealthcareService(
                specialty=service_name,
                department=department_match.group(1).strip() if department_match else None,
                healthcare_service=service_name,
                availability_confirmed=not self._is_negated(sentence, match.start()),
                evidence=SourceEvidence(supporting_text=sentence, source_url=source_url, source_title=source_title),
            ))
        return services

    @staticmethod
    def _is_negated(sentence: str, service_offset: int) -> bool:
        before = sentence[max(0, service_offset - 45):service_offset].casefold()
        after = sentence[service_offset:service_offset + 45].casefold()
        return bool(re.search(r"\b(?:no|not|without|unavailable|doesn't|does\s+not|do\s+not)\b", before)
                    or re.search(r"\b(?:unavailable|not\s+offered|not\s+available)\b", after)) and "not only" not in before

    @staticmethod
    def _sentence_for_offset(text: str, start: int, end: int) -> str:
        sentence_start = max(text.rfind(".", 0, start), text.rfind("!", 0, start), text.rfind("?", 0, start)) + 1
        sentence_end_candidates = [index for index in (text.find(".", end), text.find("!", end), text.find("?", end)) if index != -1]
        sentence_end = min(sentence_end_candidates) + 1 if sentence_end_candidates else len(text)
        return text[sentence_start:sentence_end].strip()
