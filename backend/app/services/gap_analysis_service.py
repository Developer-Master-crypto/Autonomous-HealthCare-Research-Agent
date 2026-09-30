"""Evidence-limited healthcare service availability analysis."""

from typing import Dict, Iterable, List, Optional

from backend.app.schemas.analysis import GapSeverity, ServiceGap
from backend.app.schemas.facility import Facility, Service
from backend.app.schemas.service_gap_analysis import (
    ServiceAvailabilityEvidence,
    ServiceGapAssessment,
    ServiceGapStatus,
)
from backend.app.services.distance_service import FacilityDistance
from backend.app.utils.logger import logger


class GapAnalysisService:
    """Identify comparatively limited documented availability without medical recommendations."""

    def __init__(self) -> None:
        self._gaps: Dict[str, ServiceGap] = {}

    def assess_severity_by_distance(
        self,
        distance_km: float,
        critical_threshold_km: float = 80.0,
        high_threshold_km: float = 50.0,
        medium_threshold_km: float = 30.0,
    ) -> GapSeverity:
        """Determine gap severity based on travel distance to nearest specialized care."""
        if distance_km >= critical_threshold_km:
            return GapSeverity.CRITICAL
        elif distance_km >= high_threshold_km:
            return GapSeverity.HIGH
        elif distance_km >= medium_threshold_km:
            return GapSeverity.MEDIUM
        return GapSeverity.LOW

    def record_service_gap(
        self,
        region: str,
        service_category: str,
        description: str,
        severity: GapSeverity = GapSeverity.MEDIUM,
        affected_population_estimate: Optional[int] = None,
        nearest_facility_distance_km: Optional[float] = None,
        recommended_action: Optional[str] = None,
    ) -> ServiceGap:
        """Record an identified service deficiency or medical desert."""
        gap = ServiceGap(
            region=region,
            service_category=service_category,
            severity=severity,
            description=description,
            affected_population_estimate=affected_population_estimate,
            nearest_facility_distance_km=nearest_facility_distance_km,
            recommended_action=recommended_action,
        )
        self._gaps[gap.id] = gap
        logger.info(f"Recorded healthcare service gap in [{region}]: {service_category} ({severity.value})")
        return gap

    def list_service_gaps(self) -> List[ServiceGap]:
        """List all identified service gaps."""
        return list(self._gaps.values())

    def get_service_gap(self, gap_id: str) -> Optional[ServiceGap]:
        """Retrieve a specific service gap by ID."""
        return self._gaps.get(gap_id)

    def analyze_service_availability(
        self,
        target_area: str,
        service: str,
        facilities: Iterable[Facility],
        service_evidence: Iterable[ServiceAvailabilityEvidence],
        geographic_distances: Optional[Iterable[FacilityDistance]] = None,
    ) -> ServiceGapAssessment:
        """Assess documented availability while preserving evidence and uncertainty.

        Only evidence explicitly marked as confirmed counts toward availability.
        Omitted listings, missing coordinates, and missing sources are limitations;
        they are never treated as proof that a service does not exist.
        """
        facility_list = list(facilities)
        evidence_list = list(service_evidence)
        target_service = self._normalize(service)
        distances_by_id = {
            item.facility.id: item
            for item in (geographic_distances or [])
        }
        inside_facility_ids = {
            item.facility.id for item in distances_by_id.values() if item.inside_radius
        }
        limitations: List[str] = []
        if geographic_distances is not None:
            missing_coordinates = [facility.name for facility in facility_list if facility.id not in distances_by_id]
            if missing_coordinates:
                limitations.append("Some facilities could not be geographically evaluated because coordinates were unavailable.")

        eligible_ids = inside_facility_ids if geographic_distances is not None else {facility.id for facility in facility_list}
        facility_names = {facility.id: facility.name for facility in facility_list}
        facility_ids_by_name = {
            self._normalize(facility.name): facility.id for facility in facility_list
        }
        matching_evidence = [
            item for item in evidence_list
            if self._normalize(item.service) == target_service
        ]
        confirmed_evidence = [item for item in matching_evidence if item.availability_confirmed]
        supporting_ids: List[str] = []
        for item in confirmed_evidence:
            facility_id = item.facility_id or facility_ids_by_name.get(
                self._normalize(item.facility_name)
            )
            if facility_id in eligible_ids and facility_id not in supporting_ids:
                supporting_ids.append(facility_id)
        supporting_facilities = [facility_names[facility_id] for facility_id in supporting_ids]

        unmatched_confirmed_evidence = [
            item for item in confirmed_evidence
            if (item.facility_id or facility_ids_by_name.get(self._normalize(item.facility_name)))
            not in eligible_ids
        ]
        if unmatched_confirmed_evidence:
            limitations.append(
                "Some confirming source evidence could not be matched to an evaluated "
                "facility in the target area."
            )

        if not matching_evidence:
            limitations.append("No source evidence was provided that explicitly addresses this service in the evaluated area.")
            status = ServiceGapStatus.INSUFFICIENT_EVIDENCE
            summary = f"Insufficient evidence to assess documented {service} availability in {target_area}."
        elif not supporting_facilities:
            limitations.append("Available evidence does not confirm a facility providing this service; absence from a source is not proof of absence.")
            status = ServiceGapStatus.POTENTIAL_SERVICE_GAP
            summary = f"Potential service gap: collected evidence does not confirm {service} availability in {target_area}."
        elif len(supporting_facilities) == 1:
            limitations.append("Only one facility has explicit supporting evidence in the evaluated area.")
            status = ServiceGapStatus.COMPARATIVELY_LIMITED_AVAILABILITY
            summary = f"Comparatively limited availability: one facility has documented {service} availability in {target_area}."
        else:
            status = ServiceGapStatus.AVAILABILITY_DOCUMENTED
            summary = f"Documented availability: {len(supporting_facilities)} facilities have supporting evidence for {service} in {target_area}."

        return ServiceGapAssessment(
            service=service,
            geographic_area=target_area,
            number_of_facilities_providing_service=len(supporting_facilities),
            supporting_facilities=supporting_facilities,
            evidence=matching_evidence,
            limitations=limitations,
            status=status,
            summary=summary,
        )

    def analyze_services_availability(
        self,
        target_area: str,
        facilities: Iterable[Facility],
        services: Iterable[Service],
        source_evidence: Iterable[ServiceAvailabilityEvidence],
        geographic_distances: Optional[Iterable[FacilityDistance]] = None,
    ) -> List[ServiceGapAssessment]:
        """Assess each supplied service using the same collected evidence.

        The method does not infer a missing service from the facility inventory.
        It uses service names supplied by the caller and reports only documented
        availability within the evaluated geographic scope.
        """
        facility_list = list(facilities)
        evidence_list = list(source_evidence)
        distance_list = list(geographic_distances) if geographic_distances is not None else None
        service_names: List[str] = []
        for item in services:
            if item.name not in service_names:
                service_names.append(item.name)

        return [
            self.analyze_service_availability(
                target_area=target_area,
                service=service_name,
                facilities=facility_list,
                service_evidence=evidence_list,
                geographic_distances=distance_list,
            )
            for service_name in service_names
        ]

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.casefold().split())
