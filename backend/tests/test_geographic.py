"""Tests for geographic analysis — geocoding provider, distance service, and geographic service.

All tests use known real-world coordinates and the MockGeocodingProvider.
No network calls are made; no coordinates are invented.
"""

from __future__ import annotations

from backend.app.schemas.facility import Facility, FacilityType
from backend.app.services.distance_service import (
    DistanceService,
    FacilityDistance,
)
from backend.app.services.geocoding_provider import (
    MockGeocodingProvider,
    NominatimGeocodingProvider,
    get_geocoding_provider,
)
from backend.app.services.geographic_service import GeographicService

# ============================================================
# Reference geodata (verified real-world coordinates)
# ============================================================
#   Columbus, OH      : 39.9612°N, 82.9988°W
#   Cleveland, OH     : 41.4993°N, 81.6944°W   (~200 km from Columbus)
#   Cincinnati, OH    : 39.1031°N, 84.5120°W   (~164 km from Columbus)
#   Chillicothe, OH   : 39.3328°N, 82.9824°W   (~73 km from Columbus)
#   Zanesville, OH    : 39.9403°N, 81.9940°W   (~80 km from Columbus)
# ============================================================

COLUMBUS = (39.9612, -82.9988)
CLEVELAND = (41.4993, -81.6944)
CINCINNATI = (39.1031, -84.5120)
CHILLICOTHE = (39.3328, -82.9824)
ZANESVILLE = (39.9403, -81.9940)
CHICAGO = (41.8781, -87.6298)


def _make_facility(
    name: str,
    lat: float,
    lon: float,
    state: str = "OH",
    facility_type: FacilityType = FacilityType.ACUTE_CARE_HOSPITAL,
) -> Facility:
    return Facility(
        name=name,
        facility_type=facility_type,
        latitude=lat,
        longitude=lon,
        city=name.split()[0],
        state=state,
    )


# ===========================================================
# Geocoding provider tests
# ===========================================================

class TestMockGeocodingProvider:

    def test_known_location_resolved(self):
        provider = MockGeocodingProvider()
        result = provider.geocode("Columbus, Ohio")
        assert result.success is True
        assert result.coordinates is not None
        assert abs(result.coordinates.latitude - COLUMBUS[0]) < 0.1
        assert abs(result.coordinates.longitude - COLUMBUS[1]) < 0.1
        assert result.provider == "mock_geocoding"

    def test_unknown_location_returns_failure(self):
        provider = MockGeocodingProvider()
        result = provider.geocode("Made Up Nowhere Ville, XX")
        assert result.success is False
        assert result.coordinates is None
        assert result.error_message is not None
        assert len(result.error_message) > 0

    def test_empty_query_returns_failure(self):
        provider = MockGeocodingProvider()
        result = provider.geocode("")
        # Empty queries should fail gracefully — provider can choose to return failure
        # Our mock falls through to no-match, which is correct
        assert result.success is False
        assert result.coordinates is None

    def test_custom_seeded_location(self):
        custom = {"test city, zz": (12.3456, -78.9012)}
        provider = MockGeocodingProvider(known_locations=custom)
        result = provider.geocode("Test City, ZZ")
        assert result.success is True
        assert abs(result.coordinates.latitude - 12.3456) < 0.001
        assert abs(result.coordinates.longitude - (-78.9012)) < 0.001

    def test_case_insensitive_lookup(self):
        provider = MockGeocodingProvider()
        r1 = provider.geocode("COLUMBUS, OHIO")
        r2 = provider.geocode("columbus, ohio")
        assert r1.success == r2.success

    def test_provider_name(self):
        provider = MockGeocodingProvider()
        assert provider.provider_name == "mock_geocoding"

    def test_coordinates_are_never_fabricated_for_unknown(self):
        """Core guarantee: unknown location must never return coordinates."""
        provider = MockGeocodingProvider()
        result = provider.geocode("Totally Fictional Place XYZABC")
        assert result.coordinates is None


class TestGetGeocodingProviderFactory:

    def test_mock_returned_by_default(self):
        provider = get_geocoding_provider("mock")
        assert isinstance(provider, MockGeocodingProvider)

    def test_unknown_name_falls_back_to_mock(self):
        provider = get_geocoding_provider("some_unknown_vendor")
        assert isinstance(provider, MockGeocodingProvider)

    def test_nominatim_instance_returned(self):
        provider = get_geocoding_provider("nominatim")
        assert isinstance(provider, NominatimGeocodingProvider)
        assert provider.provider_name == "nominatim_openstreetmap"


# ===========================================================
# Distance service tests
# ===========================================================

class TestDistanceService:

    def test_haversine_columbus_to_cleveland(self):
        dist = DistanceService.haversine_km(*COLUMBUS, *CLEVELAND)
        assert 195.0 <= dist <= 215.0, f"Expected ~200 km, got {dist} km"

    def test_haversine_columbus_to_cincinnati(self):
        dist = DistanceService.haversine_km(*COLUMBUS, *CINCINNATI)
        assert 155.0 <= dist <= 175.0, f"Expected ~164 km, got {dist} km"

    def test_haversine_same_point_is_zero(self):
        dist = DistanceService.haversine_km(*COLUMBUS, *COLUMBUS)
        assert dist == 0.0

    def test_haversine_symmetry(self):
        d1 = DistanceService.haversine_km(*COLUMBUS, *CLEVELAND)
        d2 = DistanceService.haversine_km(*CLEVELAND, *COLUMBUS)
        assert abs(d1 - d2) < 0.01

    def test_bearing_north(self):
        # Moving straight north: bearing should be near 0°
        bearing = DistanceService.bearing_degrees(0.0, 0.0, 1.0, 0.0)
        assert abs(bearing) < 1.0 or abs(bearing - 360.0) < 1.0

    def test_bearing_east(self):
        bearing = DistanceService.bearing_degrees(0.0, 0.0, 0.0, 1.0)
        assert abs(bearing - 90.0) < 1.0

    def test_bearing_south(self):
        bearing = DistanceService.bearing_degrees(0.0, 0.0, -1.0, 0.0)
        assert abs(bearing - 180.0) < 1.0

    def test_bearing_west(self):
        bearing = DistanceService.bearing_degrees(0.0, 0.0, 0.0, -1.0)
        assert abs(bearing - 270.0) < 1.0

    def test_facilities_partitioned_by_radius(self):
        """Chillicothe (~73 km) should be inside 100 km; Cleveland (~200 km) outside."""
        facilities = [
            _make_facility("Chillicothe Medical", *CHILLICOTHE),
            _make_facility("Cleveland Clinic", *CLEVELAND),
        ]
        inside, outside, warnings = DistanceService.facilities_with_distances(
            *COLUMBUS, facilities=facilities, radius_km=100.0
        )
        inside_names = [fd.facility.name for fd in inside]
        outside_names = [fd.facility.name for fd in outside]

        assert "Chillicothe Medical" in inside_names
        assert "Cleveland Clinic" in outside_names
        assert warnings == []

    def test_facility_without_coords_produces_warning(self):
        f = Facility(name="Mystery Clinic", facility_type=FacilityType.OTHER)
        inside, outside, warnings = DistanceService.facilities_with_distances(
            *COLUMBUS, facilities=[f], radius_km=100.0
        )
        assert inside == []
        assert outside == []
        assert len(warnings) == 1
        assert "Mystery Clinic" in warnings[0]

    def test_inside_sorted_by_distance_ascending(self):
        facilities = [
            _make_facility("Cleveland Clinic", *CLEVELAND),
            _make_facility("Chillicothe Medical", *CHILLICOTHE),
            _make_facility("Zanesville General", *ZANESVILLE),
        ]
        inside, _, _ = DistanceService.facilities_with_distances(
            *COLUMBUS, facilities=facilities, radius_km=1000.0
        )
        distances = [fd.distance_km for fd in inside]
        assert distances == sorted(distances)

    def test_cluster_by_state_groups_correctly(self):
        fds = [
            FacilityDistance(
                facility=_make_facility("A", *CLEVELAND, state="OH"),
                distance_km=200.0,
                bearing_degrees=0.0,
            ),
            FacilityDistance(
                facility=_make_facility("B", *CHILLICOTHE, state="OH"),
                distance_km=73.0,
                bearing_degrees=180.0,
            ),
            FacilityDistance(
                facility=_make_facility("C", *CHICAGO, state="IL"),
                distance_km=450.0,
                bearing_degrees=315.0,
            ),
        ]
        clusters = DistanceService.cluster_by_state(fds)
        labels = {c.region_label for c in clusters}
        assert "OH" in labels
        assert "IL" in labels
        oh_cluster = next(c for c in clusters if c.region_label == "OH")
        assert oh_cluster.count == 2


# Extra reference coordinate for clustering test
CHICAGO = (41.8781, -87.6298)


# ===========================================================
# Geographic service integration tests
# ===========================================================

class TestGeographicService:

    def _build_service(self, extra_locations: dict | None = None) -> GeographicService:
        provider = MockGeocodingProvider(known_locations=extra_locations)
        return GeographicService(geocoding_provider=provider, default_radius_km=100.0)

    def test_analyse_with_explicit_coordinates(self):
        svc = self._build_service()
        svc.register_facility(_make_facility("Chillicothe Medical", *CHILLICOTHE))
        svc.register_facility(_make_facility("Cleveland Clinic", *CLEVELAND))

        result = svc.analyse(
            target_location="Columbus, Ohio",
            target_lat=COLUMBUS[0],
            target_lon=COLUMBUS[1],
            radius_km=100.0,
        )
        assert result.total_facilities_evaluated == 2
        inside_names = [fd.facility.name for fd in result.facilities_inside_radius]
        outside_names = [fd.facility.name for fd in result.facilities_outside_radius]
        assert "Chillicothe Medical" in inside_names
        assert "Cleveland Clinic" in outside_names
        assert result.geocode_source == "user_provided"

    def test_analyse_geocodes_location_string(self):
        svc = self._build_service()
        svc.register_facility(_make_facility("Chillicothe Medical", *CHILLICOTHE))

        result = svc.analyse(
            target_location="Columbus, Ohio",
            radius_km=100.0,
        )
        assert result.success_or_not_aborted()
        assert result.geocode_source == "mock_geocoding"
        assert result.total_facilities_evaluated == 1

    def test_analyse_geocoding_failure_returns_warning(self):
        svc = self._build_service()
        result = svc.analyse(
            target_location="Totally Fictional Place XYZABC",
            radius_km=50.0,
        )
        assert len(result.warnings) > 0
        assert result.total_facilities_evaluated == 0

    def test_map_json_structure(self):
        svc = self._build_service()
        svc.register_facility(_make_facility("Chillicothe Medical", *CHILLICOTHE))
        result = svc.analyse(
            target_location="Columbus, Ohio",
            target_lat=COLUMBUS[0],
            target_lon=COLUMBUS[1],
            radius_km=100.0,
        )
        j = result.to_map_json()
        assert "target" in j
        assert "radius_km" in j
        assert "summary" in j
        assert "facilities_inside_radius" in j
        assert "facilities_outside_radius" in j
        assert "clusters" in j
        assert "warnings" in j

        target = j["target"]
        assert target["location"] == "Columbus, Ohio"
        assert abs(target["latitude"] - COLUMBUS[0]) < 0.001

    def test_facility_without_coords_produces_warning_in_analysis(self):
        svc = self._build_service()
        svc.register_facility(Facility(name="Ghost Hospital", facility_type=FacilityType.OTHER))
        result = svc.analyse(
            target_location="Columbus, Ohio",
            target_lat=COLUMBUS[0],
            target_lon=COLUMBUS[1],
        )
        assert any("Ghost Hospital" in w for w in result.warnings)

    def test_facility_without_coordinates_is_geocoded_from_explicit_address(self):
        svc = self._build_service({"123 main street, columbus, ohio": COLUMBUS})
        facility = Facility(
            name="Address Only Hospital",
            facility_type=FacilityType.ACUTE_CARE_HOSPITAL,
            address="123 Main Street",
            city="Columbus",
            state="Ohio",
        )
        result = svc.analyse(target_location="Columbus, Ohio", facilities=[facility], radius_km=10)
        entry = result.to_map_json()["facilities_inside_radius"][0]
        assert entry["coordinates_source"] == "mock_geocoding"
        assert entry["location_evidence"]["geocoding_query"] == "123 Main Street, Columbus, Ohio"

    def test_geocoding_failure_does_not_return_placeholder_coordinates(self):
        result = self._build_service().analyse(target_location="Not A Real Place")
        map_json = result.to_map_json()
        assert map_json["target"]["latitude"] is None
        assert map_json["target"]["longitude"] is None

    def test_register_and_list_facilities(self):
        svc = self._build_service()
        f1 = _make_facility("A", *COLUMBUS)
        f2 = _make_facility("B", *CLEVELAND)
        svc.register_facilities([f1, f2])
        assert len(svc.list_facilities()) == 2

    def test_find_nearest_facility(self):
        svc = self._build_service()
        svc.register_facility(_make_facility("Near", *CHILLICOTHE))
        svc.register_facility(_make_facility("Far", *CLEVELAND))

        nearest_match = svc.find_nearest_facility(*COLUMBUS)
        assert nearest_match is not None
        facility, dist = nearest_match
        assert facility.name == "Near"
        assert dist < 100.0

    def test_find_nearest_facility_no_candidates(self):
        svc = self._build_service()
        # Register facility with no coordinates
        svc.register_facility(Facility(name="Phantom", facility_type=FacilityType.OTHER))
        result = svc.find_nearest_facility(*COLUMBUS)
        assert result is None

    def test_backwards_compatible_haversine_static(self):
        dist = GeographicService.calculate_haversine_distance(*COLUMBUS, *CLEVELAND)
        assert 195.0 <= dist <= 215.0

    def test_clusters_included_in_result(self):
        svc = self._build_service()
        svc.register_facility(_make_facility("OH Facility 1", *CHILLICOTHE, state="OH"))
        svc.register_facility(_make_facility("OH Facility 2", *ZANESVILLE, state="OH"))
        svc.register_facility(_make_facility("IL Facility", *CHICAGO, state="IL"))

        result = svc.analyse(
            target_location="Columbus, Ohio",
            target_lat=COLUMBUS[0],
            target_lon=COLUMBUS[1],
            radius_km=1000.0,
        )
        cluster_labels = {c.region_label for c in result.clusters}
        assert "OH" in cluster_labels
        assert "IL" in cluster_labels

    def test_distance_preserved_in_map_json(self):
        svc = self._build_service()
        svc.register_facility(_make_facility("Chillicothe Medical", *CHILLICOTHE))
        result = svc.analyse(
            target_location="Columbus, Ohio",
            target_lat=COLUMBUS[0],
            target_lon=COLUMBUS[1],
            radius_km=100.0,
        )
        j = result.to_map_json()
        assert len(j["facilities_inside_radius"]) == 1
        entry = j["facilities_inside_radius"][0]
        assert entry["distance_km"] > 0
        assert entry["inside_radius"] is True
        assert "coordinates_source" in entry
