"""Geocoding provider abstraction for ResearchOps.

Provides a pluggable interface so the geocoding vendor (Nominatim, Google,
Mapbox, etc.) can be swapped without touching the rest of the application.
No coordinates are ever invented — if geocoding fails the error is always
surfaced explicitly.
"""

from __future__ import annotations

import time
import urllib.parse
import urllib.request
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from backend.app.utils.logger import logger


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Coordinates:
    """Immutable geographic coordinate pair with provenance metadata."""

    latitude: float
    longitude: float
    source_label: str = "unknown"           # e.g. "nominatim", "google_geocoding"
    confidence: float = 1.0                 # 0.0–1.0 reliability estimate
    raw_response: Optional[str] = None      # serialised raw payload for audit trail


@dataclass
class GeocodeResult:
    """Result returned by any geocoding provider."""

    success: bool
    coordinates: Optional[Coordinates] = None
    display_name: Optional[str] = None
    error_message: Optional[str] = None
    provider: str = "unknown"


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class BaseGeocodingProvider(ABC):
    """Abstract geocoding provider — implement this to add a new vendor."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name for telemetry and provenance."""

    @abstractmethod
    def geocode(self, location_query: str) -> GeocodeResult:
        """Resolve a location string to geographic coordinates.

        Must NEVER fabricate coordinates. Return success=False on any failure.
        """


# ---------------------------------------------------------------------------
# Nominatim (OpenStreetMap) — free, no API key required
# ---------------------------------------------------------------------------

class NominatimGeocodingProvider(BaseGeocodingProvider):
    """Geocoder using the Nominatim OpenStreetMap API (free, no API key required).

    Rate-limited to 1 request/second per the Nominatim usage policy.
    """

    BASE_URL = "https://nominatim.openstreetmap.org/search"
    USER_AGENT = "ResearchOps/0.1.0 (gateways-2026-hackathon; contact=team@spideyx.dev)"

    def __init__(self, timeout_secs: int = 5, rate_limit_secs: float = 1.0) -> None:
        self._timeout = timeout_secs
        self._rate_limit = rate_limit_secs
        self._last_request_time: float = 0.0

    @property
    def provider_name(self) -> str:
        return "nominatim_openstreetmap"

    def geocode(self, location_query: str) -> GeocodeResult:
        """Geocode via Nominatim REST API."""
        if not location_query or not location_query.strip():
            return GeocodeResult(
                success=False,
                provider=self.provider_name,
                error_message="Empty location query provided.",
            )

        # Enforce Nominatim rate limit
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._rate_limit:
            time.sleep(self._rate_limit - elapsed)

        params = urllib.parse.urlencode({
            "q": location_query.strip(),
            "format": "json",
            "limit": 1,
            "addressdetails": 0,
        })
        url = f"{self.BASE_URL}?{params}"

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": self.USER_AGENT},
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as response:
                self._last_request_time = time.monotonic()
                raw = response.read().decode("utf-8")
                data = json.loads(raw)

            if not data:
                logger.warning(f"Nominatim returned no results for: '{location_query}'")
                return GeocodeResult(
                    success=False,
                    provider=self.provider_name,
                    error_message=f"No geocoding results found for: '{location_query}'",
                )

            top = data[0]
            coords = Coordinates(
                latitude=float(top["lat"]),
                longitude=float(top["lon"]),
                source_label=self.provider_name,
                confidence=0.85,
                raw_response=json.dumps(top),
            )
            logger.info(
                f"[{self.provider_name}] Geocoded '{location_query}' "
                f"→ ({coords.latitude:.5f}, {coords.longitude:.5f})"
            )
            return GeocodeResult(
                success=True,
                coordinates=coords,
                display_name=top.get("display_name", location_query),
                provider=self.provider_name,
            )

        except Exception as exc:
            logger.error(f"[{self.provider_name}] Geocoding failed for '{location_query}': {exc}")
            return GeocodeResult(
                success=False,
                provider=self.provider_name,
                error_message=f"Geocoding request failed: {type(exc).__name__}: {exc}",
            )


# ---------------------------------------------------------------------------
# Mock provider — deterministic, no network, safe for offline tests
# ---------------------------------------------------------------------------

class MockGeocodingProvider(BaseGeocodingProvider):
    """In-memory geocoding provider for testing and offline development.

    Accepts a pre-seeded dictionary of ``location -> (lat, lon)``.
    Returns failure for any unknown location — never invents data.
    """

    def __init__(self, known_locations: Optional[dict] = None) -> None:
        # Seed with real-world reference coordinates for common US test locations
        defaults: dict = {
            "columbus, ohio": (39.9612, -82.9988),
            "cleveland, ohio": (41.4993, -81.6944),
            "cincinnati, ohio": (39.1031, -84.5120),
            "chicago, illinois": (41.8781, -87.6298),
            "new york, ny": (40.7128, -74.0060),
            "los angeles, california": (34.0522, -118.2437),
            "houston, texas": (29.7604, -95.3698),
            "appalachia, virginia": (36.9020, -82.7929),
        }
        self._locations: dict = {**defaults, **(known_locations or {})}

    @property
    def provider_name(self) -> str:
        return "mock_geocoding"

    def geocode(self, location_query: str) -> GeocodeResult:
        """Resolve from in-memory seed data — never fabricates unknown locations."""
        if not location_query or not location_query.strip():
            return GeocodeResult(
                success=False,
                provider=self.provider_name,
                error_message="Empty location query provided.",
            )
        key = location_query.strip().lower()
        match = self._locations.get(key)

        if match is None:
            # Try partial substring match
            for seed_key, coords in self._locations.items():
                if seed_key in key or key in seed_key:
                    match = coords
                    break

        if match is None:
            logger.warning(f"[{self.provider_name}] No seeded coordinates for: '{location_query}'")
            return GeocodeResult(
                success=False,
                provider=self.provider_name,
                error_message=(
                    f"Location '{location_query}' not found in mock seed data. "
                    "Add it via MockGeocodingProvider(known_locations=...)."
                ),
            )

        lat, lon = match
        coords = Coordinates(
            latitude=lat,
            longitude=lon,
            source_label=self.provider_name,
            confidence=1.0,
        )
        return GeocodeResult(
            success=True,
            coordinates=coords,
            display_name=location_query,
            provider=self.provider_name,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_geocoding_provider(
    provider_name: str = "mock",
    known_locations: Optional[dict] = None,
) -> BaseGeocodingProvider:
    """Return the requested geocoding provider instance.

    Args:
        provider_name: "nominatim" for live Nominatim OSM, "mock" for offline testing.
        known_locations: Extra seed data for the mock provider.
    """
    if provider_name == "nominatim":
        return NominatimGeocodingProvider()
    return MockGeocodingProvider(known_locations=known_locations)
