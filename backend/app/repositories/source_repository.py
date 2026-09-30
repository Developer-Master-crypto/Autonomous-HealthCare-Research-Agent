"""Repositories for sources, claims, and claim evidence."""

from typing import List, Optional

from backend.app.db.connection import DatabaseClient
from backend.app.models.db_models import ClaimEvidenceModel, ResearchClaimModel, SourceModel
from backend.app.repositories.base import BaseRepository


class SourceRepository(BaseRepository[SourceModel]):
    """Repository handling sources table operations."""

    def __init__(self, db_client: Optional[DatabaseClient] = None) -> None:
        super().__init__(
            model_class=SourceModel,
            table_name="sources",
            db_client=db_client,
        )

    def get_by_url(self, url: str, research_project_id: Optional[str] = None) -> Optional[SourceModel]:
        """Fetch a canonical URL globally or within one research project."""
        filters = {"url": url}
        if research_project_id is not None:
            filters["research_project_id"] = research_project_id
        sources = self.filter(filters)
        return sources[0] if sources else None


class ClaimRepository(BaseRepository[ResearchClaimModel]):
    """Repository handling research_claims table operations."""

    def __init__(self, db_client: Optional[DatabaseClient] = None) -> None:
        super().__init__(
            model_class=ResearchClaimModel,
            table_name="research_claims",
            db_client=db_client,
        )

    def get_claims_for_project(self, project_id: str) -> List[ResearchClaimModel]:
        """Fetch all claims linked to a research project."""
        return self.filter({"research_project_id": project_id})


class ClaimEvidenceRepository(BaseRepository[ClaimEvidenceModel]):
    """Repository handling claim_evidence table operations."""

    def __init__(self, db_client: Optional[DatabaseClient] = None) -> None:
        super().__init__(
            model_class=ClaimEvidenceModel,
            table_name="claim_evidence",
            db_client=db_client,
        )

    def get_evidence_for_claim(self, claim_id: str) -> List[ClaimEvidenceModel]:
        """Fetch all evidence citations supporting a specific claim."""
        return self.filter({"claim_id": claim_id})
