"""Distance calculation service for healthcare geographic analysis.

All distance computations use the Haversine formula (great-circle distance).
No approximations or invented coordinates are used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from backend.app.schemas.facility import Facility, FacilityType
from backend.app.services.geocoding_provider import (
    BaseGeocodingProvider,
    Coordinates,
    GeocodeResult,
    get_geocoding_provider,
)
from backend.app.utils.logger import logger


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

@dataclass
class FacilityDistance:
    """A facility paired with its computed distance from a reference point."""

    facility: Facility
    distance_km: float
    bearing_degrees: float              # 0–360, clockwise from north
    coordinates_source: str = "facility_record"   # provenance label
    location_evidence: Optional[Dict[str, Any]] = None
    inside_radius: bool = False


@dataclass
class GeographicCluster:
    """A named group of facilities sharing a geographic region."""

    cluster_id: str
    region_label: str
    centroid_lat: float
    centroid_lon: float
    facilities: List[FacilityDistance] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.facilities)


@dataclass
class GeographicAnalysisResult:
    """Map-ready JSON-serialisable result of a geographic analysis run."""

    target_location: str
    target_lat: Optional[float]
    target_lon: Optional[float]
    radius_km: float
    geocode_source: str
    total_facilities_evaluated: int
    facilities_inside_radius: List[FacilityDistance]
    facilities_outside_radius: List[FacilityDistance]
    clusters: List[GeographicCluster]
    warnings: List[str] = field(default_factory=list)

    def success_or_not_aborted(self) -> bool:
        """Return True if the analysis ran without a fatal geocoding abort."""
        return not any("aborted" in w.lower() for w in self.warnings)

    def to_map_json(self) -> Dict[str, Any]:
        """Serialise the result to map-ready JSON dict."""

        def _facility_to_dict(fd: FacilityDistance) -> Dict[str, Any]:
            f = fd.facility
            return {
                "id": f.id,
                "name": f.name,
                "facility_type": f.facility_type.value,
                "latitude": f.latitude,
                "longitude": f.longitude,
                "address": f.address,
                "city": f.city,
                "state": f.state,
                "trauma_level": f.trauma_level,
                "total_beds": f.total_beds,
                "distance_km": round(fd.distance_km, 2),
                "bearing_degrees": round(fd.bearing_degrees, 1),
                "inside_radius": fd.inside_radius,
                "coordinates_source": fd.coordinates_source,
                "location_evidence": fd.location_evidence,
            }

        return {
            "target": {
                "location": self.target_location,
                "latitude": self.target_lat,
                "longitude": self.target_lon,
                "geocode_source": self.geocode_source,
            },
            "radius_km": self.radius_km,
            "summary": {
                "total_evaluated": self.total_facilities_evaluated,
                "inside_radius": len(self.facilities_inside_radius),
                "outside_radius": len(self.facilities_outside_radius),
                "clusters": len(self.clusters),
            },
            "facilities_inside_radius": [_facility_to_dict(f) for f in self.facilities_inside_radius],
            "facilities_outside_radius": [_facility_to_dict(f) for f in self.facilities_outside_radius],
            "clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "region_label": c.region_label,
                    "centroid_lat": c.centroid_lat,
                    "centroid_lon": c.centroid_lon,
                    "facility_count": c.count,
                    "facilities": [_facility_to_dict(fd) for fd in c.facilities],
                }
                for c in self.clusters
            ],
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# Distance service
# ---------------------------------------------------------------------------

class DistanceService:
    """Computes great-circle distances, bearings, and facility groupings."""

    EARTH_RADIUS_KM = 6371.0

    @classmethod
    def haversine_km(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Return great-circle distance in kilometres between two WGS-84 points."""
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (
            math.sin(d_lat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(d_lon / 2) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return round(cls.EARTH_RADIUS_KM * c, 3)

    @classmethod
    def bearing_degrees(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Return initial bearing (0–360, clockwise from north) from point A to point B."""
        d_lon = math.radians(lon2 - lon1)
        rlat1 = math.radians(lat1)
        rlat2 = math.radians(lat2)
        x = math.sin(d_lon) * math.cos(rlat2)
        y = (
            math.cos(rlat1) * math.sin(rlat2)
            - math.sin(rlat1) * math.cos(rlat2) * math.cos(d_lon)
        )
        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360.0) % 360.0

    @classmethod
    def facilities_with_distances(
        cls,
        target_lat: float,
        target_lon: float,
        facilities: List[Facility],
        radius_km: float,
    ) -> Tuple[List[FacilityDistance], List[FacilityDistance], List[str]]:
        """Partition facilities into inside/outside radius with distances.

        Returns:
            inside, outside, warnings
        """
        inside: List[FacilityDistance] = []
        outside: List[FacilityDistance] = []
        warnings: List[str] = []

        for fac in facilities:
            if fac.latitude is None or fac.longitude is None:
                warnings.append(
                    f"Facility '{fac.name}' (id={fac.id}) has no coordinates — skipped."
                )
                continue

            dist = cls.haversine_km(target_lat, target_lon, fac.latitude, fac.longitude)
            bearing = cls.bearing_degrees(target_lat, target_lon, fac.latitude, fac.longitude)
            fd = FacilityDistance(
                facility=fac,
                distance_km=dist,
                bearing_degrees=bearing,
                coordinates_source=fac.metadata.get("coordinates_source", "facility_record"),
                location_evidence=fac.metadata.get("location_evidence"),
                inside_radius=(dist <= radius_km),
            )
            if dist <= radius_km:
                inside.append(fd)
            else:
                outside.append(fd)

        inside.sort(key=lambda x: x.distance_km)
        outside.sort(key=lambda x: x.distance_km)
        return inside, outside, warnings

    @classmethod
    def cluster_by_state(cls, facility_distances: List[FacilityDistance]) -> List[GeographicCluster]:
        """Group FacilityDistance entries by US state, computing each cluster's centroid."""
        groups: Dict[str, List[FacilityDistance]] = {}
        for fd in facility_distances:
            key = fd.facility.state or "Unknown"
            groups.setdefault(key, []).append(fd)

        clusters: List[GeographicCluster] = []
        for idx, (state, fds) in enumerate(sorted(groups.items()), start=1):
            valid = [fd for fd in fds if fd.facility.latitude is not None]
            if valid:
                centroid_lat = sum(fd.facility.latitude for fd in valid) / len(valid)  # type: ignore[arg-type]
                centroid_lon = sum(fd.facility.longitude for fd in valid) / len(valid)  # type: ignore[arg-type]
            else:
                centroid_lat = 0.0
                centroid_lon = 0.0

            clusters.append(
                GeographicCluster(
                    cluster_id=f"cluster_{idx:03d}",
                    region_label=state,
                    centroid_lat=centroid_lat,
                    centroid_lon=centroid_lon,
                    facilities=fds,
                )
            )

        return clusters
