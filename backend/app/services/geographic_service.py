"""Geographic analysis service for ResearchOps.

Orchestrates geocoding, distance computation, radius filtering, geographic
clustering, and returns map-ready JSON output.

Key guarantees:
- Coordinates are NEVER invented; missing coords surface as explicit warnings.
- Every coordinate in the output carries a provenance label (coordinates_source).
- Geocoding failures are always reported explicitly — never silently swallowed.
- The geocoding provider is injected so vendors can be swapped without code changes.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from backend.app.schemas.facility import Facility
from backend.app.services.distance_service import (
    DistanceService,
    FacilityDistance,
    GeographicAnalysisResult,
    GeographicCluster,
)
from backend.app.services.geocoding_provider import (
    BaseGeocodingProvider,
    Coordinates,
    GeocodeResult,
    get_geocoding_provider,
)
from backend.app.utils.logger import logger


class GeographicService:
    """Healthcare facility geographic analysis service.

    Accepts target location strings or raw coordinates, geocodes when needed,
    calculates distances, identifies facilities inside a radius, groups them
    geographically, and returns map-ready JSON.
    """

    def __init__(
        self,
        geocoding_provider: Optional[BaseGeocodingProvider] = None,
        default_radius_km: float = 80.0,
    ) -> None:
        self._geocoder: BaseGeocodingProvider = geocoding_provider or get_geocoding_provider("mock")
        self._default_radius_km = default_radius_km
        self._facilities: Dict[str, Facility] = {}

    # ------------------------------------------------------------------
    # Facility registry
    # ------------------------------------------------------------------

    def register_facility(self, facility: Facility) -> Facility:
        """Register a facility into the in-memory spatial store.

        Coordinates are taken only from the Facility record — never invented.
        """
        self._facilities[facility.id] = facility
        coord_status = "with coordinates" if facility.latitude is not None else "NO coordinates"
        logger.info(f"Registered facility [{facility.id}] '{facility.name}' ({coord_status})")
        return facility

    def register_facilities(self, facilities: List[Facility]) -> None:
        """Bulk register a list of facilities."""
        for f in facilities:
            self.register_facility(f)

    def get_facility(self, facility_id: str) -> Optional[Facility]:
        """Retrieve a registered facility by ID."""
        return self._facilities.get(facility_id)

    def list_facilities(self) -> List[Facility]:
        """Return all registered facilities."""
        return list(self._facilities.values())

    # ------------------------------------------------------------------
    # Geocoding
    # ------------------------------------------------------------------

    def resolve_coordinates(
        self,
        location_query: str,
        provided_lat: Optional[float] = None,
        provided_lon: Optional[float] = None,
    ) -> Tuple[Optional[Coordinates], Optional[str]]:
        """Resolve target coordinates from explicit values or geocoder.

        Returns (Coordinates, error_message). Exactly one will be non-None.
        Never fabricates coordinates — returns error on any failure.
        """
        # Explicit coordinates take priority — no geocoding needed
        if provided_lat is not None and provided_lon is not None:
            coords = Coordinates(
                latitude=provided_lat,
                longitude=provided_lon,
                source_label="user_provided",
                confidence=1.0,
            )
            return coords, None

        # Geocode the location string
        result: GeocodeResult = self._geocoder.geocode(location_query)
        if result.success and result.coordinates is not None:
            return result.coordinates, None

        error = result.error_message or f"Geocoding failed for '{location_query}'"
        logger.warning(f"Geocoding failure: {error}")
        return None, error

    # ------------------------------------------------------------------
    # Core analysis
    # ------------------------------------------------------------------

    def analyse(
        self,
        target_location: str,
        facilities: Optional[List[Facility]] = None,
        radius_km: Optional[float] = None,
        target_lat: Optional[float] = None,
        target_lon: Optional[float] = None,
    ) -> GeographicAnalysisResult:
        """Perform a full geographic analysis run.

        Args:
            target_location: Human-readable location name (used for geocoding when coordinates not provided).
            facilities: Facilities to evaluate. Uses registered facilities when None.
            radius_km: Radius threshold in kilometres (defaults to ``self._default_radius_km``).
            target_lat: Explicit target latitude (skips geocoding when provided with target_lon).
            target_lon: Explicit target longitude.

        Returns:
            GeographicAnalysisResult — serialise via ``.to_map_json()`` for map clients.
        """
        effective_radius = radius_km if radius_km is not None else self._default_radius_km
        pool = facilities if facilities is not None else list(self._facilities.values())
        warnings: List[str] = []

        # 1. Resolve target coordinates
        coords, geo_error = self.resolve_coordinates(
            location_query=target_location,
            provided_lat=target_lat,
            provided_lon=target_lon,
        )

        if coords is None:
            # Cannot proceed without a target coordinate — return empty result with error
            warnings.append(f"Geographic analysis aborted: {geo_error}")
            logger.error(f"Geographic analysis cannot proceed: {geo_error}")
            return GeographicAnalysisResult(
                target_location=target_location,
                target_lat=None,
                target_lon=None,
                radius_km=effective_radius,
                geocode_source="none",
                total_facilities_evaluated=0,
                facilities_inside_radius=[],
                facilities_outside_radius=[],
                clusters=[],
                warnings=warnings,
            )

        logger.info(
            f"Geographic analysis: target='{target_location}' "
            f"({coords.latitude:.5f}, {coords.longitude:.5f}) "
            f"radius={effective_radius} km, facilities={len(pool)}"
        )

        resolved_facilities, facility_warnings = self._resolve_facility_coordinates(pool)
        warnings.extend(facility_warnings)

        # 2. Compute distances and partition
        inside, outside, dist_warnings = DistanceService.facilities_with_distances(
            target_lat=coords.latitude,
            target_lon=coords.longitude,
            facilities=resolved_facilities,
            radius_km=effective_radius,
        )
        warnings.extend(dist_warnings)

        # 3. Cluster all facilities geographically
        clusters = DistanceService.cluster_by_state(inside + outside)

        return GeographicAnalysisResult(
            target_location=target_location,
            target_lat=coords.latitude,
            target_lon=coords.longitude,
            radius_km=effective_radius,
            geocode_source=coords.source_label,
            total_facilities_evaluated=len(pool),
            facilities_inside_radius=inside,
            facilities_outside_radius=outside,
            clusters=clusters,
            warnings=warnings,
        )

    def _resolve_facility_coordinates(self, facilities: List[Facility]) -> Tuple[List[Facility], List[str]]:
        """Geocode facilities only from their explicit address components when needed."""
        resolved: List[Facility] = []
        warnings: List[str] = []
        for facility in facilities:
            if facility.latitude is not None and facility.longitude is not None:
                resolved.append(facility)
                continue
            location_query = ", ".join(
                component for component in (facility.address, facility.city, facility.state, facility.zip_code) if component
            )
            if not location_query:
                resolved.append(facility)
                continue
            result = self._geocoder.geocode(location_query)
            if not result.success or result.coordinates is None:
                warnings.append(f"Facility '{facility.name}' could not be geocoded: {result.error_message or 'unknown error'}")
                resolved.append(facility)
                continue
            metadata = dict(facility.metadata)
            metadata["coordinates_source"] = result.coordinates.source_label
            metadata["location_evidence"] = {
                "geocoding_query": location_query,
                "provider": result.provider,
                "display_name": result.display_name,
            }
            resolved.append(facility.model_copy(update={
                "latitude": result.coordinates.latitude,
                "longitude": result.coordinates.longitude,
                "metadata": metadata,
            }))
        return resolved, warnings

    # ------------------------------------------------------------------
    # Convenience helpers (backwards-compatible with earlier interface)
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_haversine_distance(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Static Haversine wrapper for backwards compatibility."""
        return DistanceService.haversine_km(lat1, lon1, lat2, lon2)

    def find_nearest_facility(
        self,
        lat: float,
        lon: float,
        facilities: Optional[List[Facility]] = None,
    ) -> Optional[Tuple[Facility, float]]:
        """Return (nearest_facility, distance_km) or None if no candidates."""
        pool = facilities if facilities is not None else list(self._facilities.values())
        valid = [f for f in pool if f.latitude is not None and f.longitude is not None]
        if not valid:
            return None

        nearest: Optional[Facility] = None
        min_dist = float("inf")
        for fac in valid:
            d = DistanceService.haversine_km(lat, lon, fac.latitude, fac.longitude)  # type: ignore[arg-type]
            if d < min_dist:
                min_dist = d
                nearest = fac

        return (nearest, min_dist) if nearest else None
