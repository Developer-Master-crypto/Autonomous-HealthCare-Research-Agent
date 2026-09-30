"""Evidence verification with transparent support and conflict rules."""

from typing import Dict, List, Optional
from backend.app.schemas.source import ResearchClaim, ResearchSource
from backend.app.schemas.analysis import Conflict, ConflictStatus
from backend.app.utils.logger import logger
from backend.app.schemas.verification import (
    ClaimEvidenceRecord,
    ClaimVerificationResult,
    EvidenceRelation,
    VerificationStatus,
    VerifiableClaim,
)
from backend.app.services.claim_service import ClaimService
from backend.app.services.conflict_service import ConflictService


class VerificationService:
    """Detects discrepancies between independent healthcare assertions and manages conflict state."""

    def __init__(self, claim_service: Optional[ClaimService] = None, conflict_service: Optional[ConflictService] = None) -> None:
        self._conflicts: Dict[str, Conflict] = {}
        self.claim_service = claim_service or ClaimService()
        self.conflict_service = conflict_service or ConflictService()

    def verify_claim(
        self,
        claim: VerifiableClaim,
        evidence: List[ClaimEvidenceRecord],
    ) -> ClaimVerificationResult:
        """Verify a claim using explicit evidence, never a fabricated confidence score.

        Supported requires two independent source URLs that explicitly support the
        claim. Any explicit contradiction is retained and makes the outcome
        conflicting. One source, no evidence, and non-independent duplicates are
        insufficient evidence.
        """
        unique_evidence = self.claim_service.deduplicate_evidence(evidence)
        conflicts = self.conflict_service.detect(claim, unique_evidence)
        if conflicts:
            status = VerificationStatus.CONFLICTING
        else:
            supporting_urls = {
                item.source_url.rstrip("/")
                for item in unique_evidence
                if item.relation == EvidenceRelation.SUPPORTS
            }
            status = (
                VerificationStatus.SUPPORTED
                if len(supporting_urls) >= 2
                else VerificationStatus.INSUFFICIENT_EVIDENCE
            )
        return ClaimVerificationResult(claim=claim, status=status, evidence=unique_evidence, conflicts=conflicts)

    def flag_conflict(
        self,
        topic: str,
        claim_a: ResearchClaim,
        claim_b: ResearchClaim,
        description: str,
        status: ConflictStatus = ConflictStatus.UNRESOLVED,
    ) -> Conflict:
        """Register a contradiction detected between two distinct evidence claims."""
        conflict = Conflict(
            topic=topic,
            claim_a=claim_a,
            claim_b=claim_b,
            description=description,
            resolution_status=status,
        )
        self._conflicts[conflict.id] = conflict
        logger.warning(f"Evidentiary conflict flagged on topic '{topic}': {description}")
        return conflict

    def list_conflicts(self) -> List[Conflict]:
        """List all detected evidentiary conflicts."""
        return list(self._conflicts.values())

    def get_conflict(self, conflict_id: str) -> Optional[Conflict]:
        """Retrieve a specific conflict by ID."""
        return self._conflicts.get(conflict_id)
