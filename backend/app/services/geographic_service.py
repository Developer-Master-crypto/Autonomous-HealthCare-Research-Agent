"""Geographic and spatial calculation service for healthcare accessibility."""

import math
from typing import Dict, List, Optional, Tuple
from backend.app.schemas.facility import Facility
from backend.app.utils.logger import logger


class GeographicService:
    """Performs spatial analysis, distance computations, and facility proximity clustering."""

    def __init__(self) -> None:
        self._facilities: Dict[str, Facility] = {}

    @staticmethod
    def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Compute the great-circle distance between two geographic coordinates in kilometers."""
        earth_radius_km = 6371.0

        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)

        a = (
            math.sin(d_lat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(d_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(earth_radius_km * c, 2)

    def register_facility(self, facility: Facility) -> Facility:
        """Register a healthcare facility entity into spatial storage."""
        self._facilities[facility.id] = facility
        logger.info(f"Registered facility [{facility.id}] {facility.name}")
        return facility

    def get_facility(self, facility_id: str) -> Optional[Facility]:
        """Retrieve facility by identifier."""
        return self._facilities.get(facility_id)

    def list_facilities(self) -> List[Facility]:
        """List all registered facilities."""
        return list(self._facilities.values())

    def find_nearest_facility(
        self,
        lat: float,
        lon: float,
        facilities: Optional[List[Facility]] = None,
    ) -> Optional[Tuple[Facility, float]]:
        """Identify the closest facility to a given coordinate point and return (facility, distance_km)."""
        pool = facilities if facilities is not None else list(self._facilities.values())
        valid_pool = [f for f in pool if f.latitude is not None and f.longitude is not None]

        if not valid_pool:
            return None

        nearest_fac: Optional[Facility] = None
        min_distance = float("inf")

        for fac in valid_pool:
            dist = self.calculate_haversine_distance(lat, lon, fac.latitude, fac.longitude)
            if dist < min_distance:
                min_distance = dist
                nearest_fac = fac

        if nearest_fac:
            return nearest_fac, min_distance
        return None
