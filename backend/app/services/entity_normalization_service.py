"""Conservative facility identity matching without speculative merging."""

import re
from typing import Iterable, Optional

from pydantic import BaseModel

from backend.app.schemas.facility_extraction import ExtractedFacility


class NormalizationDecision(BaseModel):
    """Result of an identity check, including why a merge is or is not safe."""

    matched_facility_name: Optional[str] = None
    should_merge: bool
    reason: str


class EntityNormalizationService:
    """Match facilities only when name and a second exact identity anchor agree."""

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize punctuation and whitespace for exact-name comparison only."""
        return re.sub(r"[^a-z0-9]", "", name.lower())

    def compare(self, candidate: ExtractedFacility, existing: ExtractedFacility) -> NormalizationDecision:
        """Return a merge decision without inferring identity from name similarity."""
        if self.normalize_name(candidate.name) != self.normalize_name(existing.name):
            return NormalizationDecision(should_merge=False, reason="Facility names are not an exact normalized match.")
        if candidate.website and existing.website and candidate.website.rstrip("/") == existing.website.rstrip("/"):
            return NormalizationDecision(matched_facility_name=existing.name, should_merge=True, reason="Exact normalized name and website match.")
        if candidate.address and existing.address and candidate.address.casefold().strip() == existing.address.casefold().strip():
            return NormalizationDecision(matched_facility_name=existing.name, should_merge=True, reason="Exact normalized name and address match.")
        return NormalizationDecision(should_merge=False, reason="A second matching identity anchor is required before merging facilities.")

    def find_safe_match(self, candidate: ExtractedFacility, existing_facilities: Iterable[ExtractedFacility]) -> Optional[ExtractedFacility]:
        """Find at most one safely mergeable facility."""
        matches = [facility for facility in existing_facilities if self.compare(candidate, facility).should_merge]
        return matches[0] if len(matches) == 1 else None
