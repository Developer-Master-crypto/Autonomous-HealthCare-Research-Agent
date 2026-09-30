"""Healthcare service-gap and medical desert analysis service."""

from typing import Dict, List, Optional
from backend.app.schemas.facility import Facility, Service
from backend.app.schemas.analysis import ServiceGap, GapSeverity
from backend.app.utils.logger import logger


class GapAnalysisService:
    """Evaluates geographic access barriers and specialized clinical service deficits."""

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
